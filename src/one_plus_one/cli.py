"""CLI entry point for data layer operations."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import typer
import sqlite_vec

from one_plus_one.models import init_db, Project
from one_plus_one.store import Store
from one_plus_one.retriever import Retriever

app = typer.Typer(name="oneplusone", help="1+1>2 GitHub project inspiration synthesizer", add_completion=False)

DB_PATH = Path(os.environ.get("ONEPLUSONE_DB", Path(__file__).parent.parent.parent / "data" / "projects.db"))


def get_db() -> sqlite3.Connection:
    """Get or create database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    init_db(conn)
    return conn


@app.command()
def crawl_trending(
    since: str = typer.Option("daily", help="daily, weekly, or monthly"),
):
    """Crawl GitHub trending repos."""
    import asyncio
    from one_plus_one.crawler.github import GitHubClient

    async def _run():
        client = GitHubClient(token=os.environ.get("GITHUB_TOKEN"))
        try:
            repos = await client.fetch_trending_repos(since)
            print(f"Found {len(repos)} trending repos ({since})")
            for r in repos:
                print(f"  - {r['owner']}/{r['name']} ({r.get('stars', 0)} stars)")

            # Fetch full README for each
            conn = get_db()
            store = Store(conn)
            for repo in repos:
                full = await client.fetch_repo(repo["owner"], repo["name"])
                if full:
                    pid = store.insert_or_update(full)
                    print(f"    Saved: {full.full_name} (id={pid})")
            conn.close()
            print(f"Done. Total in DB: {len(repos)}")
        finally:
            await client.close()

    asyncio.run(_run())


@app.command("crawl_mass")
def crawl_mass():
    """Mass crawl trending (daily/weekly/monthly) + popular topics."""
    import asyncio
    import time
    from one_plus_one.crawler.github import GitHubClient

    async def _run():
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("⚠️  No GITHUB_TOKEN found. Using unauthenticated API (60 req/hr limit). Will use fallbacks.")
            
        client = GitHubClient(token=token)
        conn = get_db()
        store = Store(conn)
        
        saved_count = 0
        
        # 1. Trending (all timeframes) - Uses scraper fallback
        for since in ["daily", "weekly", "monthly"]:
            try:
                repos = await client.fetch_trending_repos(since)
                print(f"Trending ({since}): {len(repos)} repos")
                for repo in repos:
                    full = await client.fetch_repo(repo["owner"], repo["name"])
                    if full:
                        # Merge initial data (stars, description) if API missed it
                        if not full.stars and repo.get("stars"):
                            full.stars = repo["stars"]
                        if not full.description and repo.get("description"):
                            full.description = repo["description"]
                        store.insert_or_update(full)
                        saved_count += 1
                        print(f"  [+] {full.full_name} (⭐ {full.stars})")
            except Exception as e:
                print(f"Error crawling trending ({since}): {e}")

        # 2. Topics - Uses API (respects rate limits)
        topics = ["ai", "llm", "agent", "machine-learning", "generative", "rag", "local-llm"]
        for topic in topics:
            try:
                repos = await client.fetch_by_topic(topic, limit=20)
                print(f"Topic '{topic}': {len(repos)} repos")
                for repo in repos:
                    full = await client.fetch_repo(repo["owner"], repo["name"])
                    if full:
                        store.insert_or_update(full)
                        saved_count += 1
                    time.sleep(1.5)  # Slow down to avoid 403
            except Exception as e:
                print(f"Error crawling topic {topic}: {e}")

        conn.close()
        print(f"\n✅ Mass crawl finished. Saved {saved_count} new/updated projects.")

    asyncio.run(_run())


@app.command("crawl_topic")
def crawl_topic(
    topics: list[str] = typer.Argument(..., help="Topics to search"),
    limit: int = typer.Option(50, help="Max repos per topic"),
):
    """Crawl repos by topic."""
    import asyncio
    from one_plus_one.crawler.github import GitHubClient

    async def _run():
        client = GitHubClient(token=os.environ.get("GITHUB_TOKEN"))
        try:
            conn = get_db()
            store = Store(conn)
            for topic in topics:
                repos = await client.fetch_by_topic(topic, limit=limit)
                print(f"Topic '{topic}': {len(repos)} repos")
                for repo in repos:
                    full = await client.fetch_repo(repo["owner"], repo["name"])
                    if full:
                        store.insert_or_update(full)
                        print(f"  - {full.full_name}")
            count = store.count()
            conn.close()
            print(f"Total in DB: {count}")
        finally:
            await client.close()

    asyncio.run(_run())


@app.command("crawl_repo")
def crawl_repo(
    url: str = typer.Argument(..., help="GitHub repo URL or owner/name"),
):
    """Crawl a single repo."""
    import asyncio
    import re
    from one_plus_one.crawler.github import GitHubClient

    async def _run():
        # Parse URL or owner/name
        m = re.search(r"github\.com/([^/]+/[^/]+)", url)
        if m:
            owner, name = m.group(1).split("/")
        elif "/" in url:
            owner, name = url.split("/", 1)
        else:
            print("Invalid URL. Use: github.com/owner/name or owner/name")
            raise typer.Exit(1)

        client = GitHubClient(token=os.environ.get("GITHUB_TOKEN"))
        try:
            project = await client.fetch_repo(owner, name)
            if not project:
                print(f"Repo not found: {owner}/{name}")
                raise typer.Exit(1)

            conn = get_db()
            store = Store(conn)
            pid = store.insert_or_update(project)
            print(f"Saved: {project.full_name} ({project.stars} stars, id={pid})")
            conn.close()
        finally:
            await client.close()

    asyncio.run(_run())


@app.command()
def index(
    all: bool = typer.Option(False, help="Index all unindexed projects"),
):
    """Index unindexed projects with embeddings."""
    conn = get_db()
    store = Store(conn)

    # Lazy import — only load model when needed
    from one_plus_one.embedder import BgeM3Embedder, prepare_embed_text

    embedder = BgeM3Embedder()

    projects = store.get_unindexed(limit=500)
    print(f"Found {len(projects)} unindexed projects")

    for i, pdata in enumerate(projects):
        project_dict = dict(pdata)
        text = prepare_embed_text(project_dict)
        vec = embedder.encode(text)
        store.insert_vector(pdata["id"], vec)
        if (i + 1) % 10 == 0:
            print(f"  Indexed {i + 1}/{len(projects)}")

    conn.close()
    print(f"Done. Total indexed: {len(projects)}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    top: int = typer.Option(10, help="Number of results"),
    language: str = typer.Option(None, help="Filter by language"),
    min_stars: int = typer.Option(None, help="Minimum stars"),
):
    """Search for projects semantically."""
    from one_plus_one.embedder import BgeM3Embedder

    conn = get_db()
    store = Store(conn)
    embedder = BgeM3Embedder()
    retriever = Retriever(store, embedder)

    results = retriever.search(query, k=top, language=language, min_stars=min_stars)
    if not results:
        print("No results found.")
        return

    for r in results:
        stars = f"{r['stars']:,}"
        lang = f" [{r['language']}]" if r.get("language") else ""
        print(f"\n{r['full_name']} ({stars} stars){lang}")
        print(f"  {r['description']}")
        if r.get("readme_excerpt"):
            print(f"  {r['readme_excerpt'][:200]}...")

    conn.close()


@app.command()
def stats():
    """Show database statistics."""
    from one_plus_one.embedder import BgeM3Embedder

    conn = get_db()
    store = Store(conn)
    embedder = BgeM3Embedder()
    retriever = Retriever(store, embedder)

    status = retriever.db_status()
    print(f"Total projects: {status['total_projects']}")
    print(f"Indexed (with vectors): {status['indexed_projects']}")
    print("Top languages:")
    for lang, count in status["top_languages"].items():
        print(f"  {lang}: {count}")

    conn.close()


@app.command("db_info")
def db_info():
    """Show database file info."""
    if DB_PATH.exists():
        size = DB_PATH.stat().st_size / (1024 * 1024)
        print(f"DB path: {DB_PATH}")
        print(f"DB size: {size:.1f} MB")
    else:
        print(f"No database found at {DB_PATH}")


@app.command("report")
def generate_report(
    top: int = typer.Option(10, help="Number of projects to feature"),
    output: str = typer.Option(None, help="Save report to file"),
):
    """Generate daily report of top projects."""
    conn = get_db()
    from one_plus_one.daily_report import generate_daily_report
    
    report = generate_daily_report(conn, top_k=top)
    print(report)
    
    if output:
        Path(output).write_text(report, encoding="utf-8")
        print(f"\n💾 Report saved to: {output}")
        
    conn.close()


@app.command()
def inspire(
    idea: str = typer.Argument(..., help="Your project idea"),
    top: int = typer.Option(5, help="Number of candidate projects to show"),
    output: str = typer.Option(None, help="Save synthesis report to file"),
):
    """Progressive inspiration: search → select 2 → synthesize."""
    from one_plus_one.embedder import BgeM3Embedder
    from one_plus_one.synthesizer import Synthesizer
    from one_plus_one.assessor import CompetitionAssessor

    conn = get_db()
    store = Store(conn)
    embedder = BgeM3Embedder()
    retriever = Retriever(store, embedder)

    # Step 1: Search related projects
    print(f"\n💡 Idea: {idea}")
    print(f"\n📊 竞争度评估...")
    candidates = retriever.search(idea, k=20)
    assessment = CompetitionAssessor.assess(candidates, idea)
    print(assessment["summary"])

    print(f"\n📋 相关项目 (Top {min(top, len(candidates))}):")
    if not candidates:
        print("  未找到相关项目。尝试爬取更多数据后再试。")
        conn.close()
        return

    for i, r in enumerate(candidates[:top], 1):
        stars = f"{r['stars']:,}"
        lang = f" [{r['language']}]" if r.get("language") else ""
        print(f"  {i}. {r['full_name']} ({stars} stars){lang}")
        print(f"     {r['description']}")

    if len(candidates) < 2:
        print("\n⚠️ 需要至少 2 个项目才能合成。请爬取更多数据。")
        conn.close()
        return

    # Step 2: Select 2 projects (auto-select top 2 by quality_score)
    selected = sorted(candidates[:top], key=lambda x: x.get("quality_score", 0), reverse=True)[:2]

    print(f"\n🔬 自动选择 Top 2 项目进行合成...")
    print(f"  A: {selected[0]['full_name']} (quality: {selected[0].get('quality_score', 0):.0f})")
    print(f"  B: {selected[1]['full_name']} (quality: {selected[1].get('quality_score', 0):.0f})")

    # Step 3: Synthesize
    print(f"\n⚡ 生成组合方案...")
    report = Synthesizer.synthesize(selected[0], selected[1])

    # Step 4: Output
    markdown = report.to_markdown()
    print(f"\n{markdown}")

    if output:
        Path(output).write_text(markdown, encoding="utf-8")
        print(f"\n💾 报告已保存到: {output}")

    conn.close()


if __name__ == "__main__":
    app()
