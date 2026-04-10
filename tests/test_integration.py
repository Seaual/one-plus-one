"""Integration test: full crawl → index → search flow."""

import sqlite3

import sqlite_vec

from one_plus_one.models import init_db, Project
from one_plus_one.store import Store
from one_plus_one.retriever import Retriever


def _setup_db():
    conn = sqlite3.connect(":memory:")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    init_db(conn)
    return conn


def test_full_flow(mock_embedder):
    """Simulate: crawl data → store → index → search."""
    conn = _setup_db()
    store = Store(conn)

    # Simulate crawled data
    crawled = [
        {"owner": "ai-org", "name": "ml-framework", "description": "A machine learning framework for building AI models", "stars": 15000, "language": "Python"},
        {"owner": "web-dev", "name": "react-ui", "description": "React UI component library for building web apps", "stars": 8000, "language": "TypeScript"},
        {"owner": "data-sci", "name": "ai-pipeline", "description": "AI data pipeline for processing and training ML models", "stars": 3000, "language": "Python"},
    ]

    for data in crawled:
        p = Project.from_dict(data)
        pid = store.insert_or_update(p)
        vec = mock_embedder.encode(data["description"])
        store.insert_vector(pid, vec)

    # Search
    retriever = Retriever(store, mock_embedder)
    results = retriever.search("machine learning framework", k=5)

    assert len(results) >= 2
    names = [r["name"] for r in results]
    assert "ml-framework" in names

    # Filter by language
    py_results = retriever.search("framework", k=5, language="Python")
    for r in py_results:
        assert r["language"] == "Python"

    # Status
    status = retriever.db_status()
    assert status["total_projects"] == 3
    assert status["indexed_projects"] == 3

    conn.close()


def test_mcp_tools_output_format(mock_embedder):
    """Test that MCP tool outputs are well-formatted."""
    conn = _setup_db()
    store = Store(conn)
    retriever = Retriever(store, mock_embedder)

    p = Project.from_dict({"owner": "test", "name": "demo", "description": "Demo project", "stars": 100})
    pid = store.insert_or_update(p)
    store.insert_vector(pid, mock_embedder.encode("Demo project"))

    # Verify search output format
    results = retriever.search("demo", k=5)
    assert len(results) == 1
    assert "full_name" in results[0]
    assert "readme_excerpt" in results[0]
    assert len(results[0]["readme_excerpt"]) <= 500

    # Verify project_detail
    detail = retriever.project_detail("test/demo")
    assert detail is not None
    assert "url" in detail

    conn.close()
