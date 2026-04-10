"""MCP Server exposing 1+1>2 tools to Claude Code."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import sqlite_vec
from mcp.server.fastmcp import FastMCP

from one_plus_one.models import init_db
from one_plus_one.store import Store
from one_plus_one.retriever import Retriever
from one_plus_one.embedder import BgeM3Embedder

# Lazy initialization — model only loads when first tool is called
_db_conn = None
_retriever = None


def _get_retriever() -> Retriever:
    """Get or create retriever singleton."""
    global _db_conn, _retriever
    if _retriever is None:
        db_path = Path(os.environ.get("ONEPLUSONE_DB", Path(__file__).parent.parent.parent / "data" / "projects.db"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db_conn = sqlite3.connect(str(db_path))
        _db_conn.enable_load_extension(True)
        sqlite_vec.load(_db_conn)
        init_db(_db_conn)
        store = Store(_db_conn)
        embedder = BgeM3Embedder()
        _retriever = Retriever(store, embedder)
    return _retriever


mcp = FastMCP("one-plus-one")


@mcp.tool()
def search_projects(
    query: str,
    k: int = 10,
    language: str | None = None,
    min_stars: int | None = None,
) -> str:
    """Search for GitHub projects semantically related to the query.

    Args:
        query: The search query describing what you're looking for
        k: Number of results (default 10)
        language: Optional filter by programming language
        min_stars: Optional minimum star count filter
    """
    retriever = _get_retriever()
    results = retriever.search(query, k=k, language=language, min_stars=min_stars)
    if not results:
        return "No projects found matching your query."

    lines = [f"Found {len(results)} related projects:\n"]
    for r in results:
        stars = f"{r['stars']:,}"
        lang = f" [{r['language']}]" if r.get("language") else ""
        lines.append(f"## {r['full_name']} ({stars} stars){lang}")
        lines.append(f"  {r['description']}")
        if r.get("topics"):
            lines.append(f"  Topics: {', '.join(r['topics'][:5])}")
        if r.get("readme_excerpt"):
            lines.append(f"  Preview: {r['readme_excerpt'][:200]}...")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def project_detail(full_name: str) -> str:
    """Get full details of a specific GitHub project.

    Args:
        full_name: The full repository name (owner/repo)
    """
    retriever = _get_retriever()
    detail = retriever.project_detail(full_name)
    if not detail:
        return f"Project '{full_name}' not found in database."

    lines = [
        f"# {detail['full_name']}",
        f"**URL**: {detail['url']}",
        f"**Stars**: {detail['stars']:,}",
        f"**Language**: {detail['language'] or 'N/A'}",
        f"**Description**: {detail['description']}",
        f"**Topics**: {', '.join(detail['topics'])}" if detail.get('topics') else "",
    ]
    if detail.get("readme"):
        lines.append(f"\n## README\n{detail['readme'][:2000]}...")

    return "\n".join(lines)


@mcp.tool()
def db_status() -> str:
    """Get statistics about the local project database."""
    retriever = _retriever or _get_retriever()
    status = retriever.db_status()
    lines = [
        f"**Total projects**: {status['total_projects']}",
        f"**Indexed (with vectors)**: {status['indexed_projects']}",
        "**Top languages**:",
    ]
    for lang, count in status.get("top_languages", {}).items():
        lines.append(f"  - {lang}: {count}")
    return "\n".join(lines)


def run():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    run()
