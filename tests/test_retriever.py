"""Tests for the semantic search retriever."""

import json

from one_plus_one.models import Project
from one_plus_one.retriever import Retriever
from one_plus_one.store import Store


def _add_project(store: Store, embedder, owner: str, name: str, desc: str, stars: int = 100, language: str = "Python"):
    """Helper to add a project with its vector."""
    p = Project.from_dict({
        "owner": owner, "name": name,
        "description": desc, "stars": stars, "language": language,
    })
    pid = store.insert_or_update(p)
    vec = embedder.encode(desc)
    store.insert_vector(pid, vec)
    return pid


def test_search_returns_related_projects(db_conn, mock_embedder):
    store = Store(db_conn)
    retriever = Retriever(store, mock_embedder)

    _add_project(store, mock_embedder, "a", "ml-lib", "Machine learning library for data scientists", 5000)
    _add_project(store, mock_embedder, "b", "web-app", "A web application framework", 3000)
    _add_project(store, mock_embedder, "c", "ai-toolkit", "AI toolkit for developers", 8000)

    results = retriever.search("machine learning AI", k=5)
    assert len(results) >= 2
    # Should prefer AI/ML projects
    names = [r["name"] for r in results]
    assert "ml-lib" in names
    assert "ai-toolkit" in names


def test_search_with_language_filter(db_conn, mock_embedder):
    store = Store(db_conn)
    retriever = Retriever(store, mock_embedder)

    _add_project(store, mock_embedder, "a", "py-ml", "Python ML library", 100, "Python")
    _add_project(store, mock_embedder, "b", "go-ml", "Go ML library", 100, "Go")

    results = retriever.search("ML", k=5, language="Python")
    assert len(results) == 1
    assert results[0]["name"] == "py-ml"


def test_search_with_min_stars(db_conn, mock_embedder):
    store = Store(db_conn)
    retriever = Retriever(store, mock_embedder)

    _add_project(store, mock_embedder, "a", "big-project", "Popular project", 10000)
    _add_project(store, mock_embedder, "b", "small-project", "Small project", 50)

    results = retriever.search("project", k=5, min_stars=1000)
    assert len(results) == 1
    assert results[0]["name"] == "big-project"


def test_search_empty_db(db_conn, mock_embedder):
    store = Store(db_conn)
    retriever = Retriever(store, mock_embedder)
    results = retriever.search("anything")
    assert results == []


def test_project_detail(db_conn, mock_embedder):
    store = Store(db_conn)
    retriever = Retriever(store, mock_embedder)

    _add_project(store, mock_embedder, "test", "myrepo", "My repo desc")
    detail = retriever.project_detail("test/myrepo")
    assert detail is not None
    assert detail["name"] == "myrepo"
    assert detail["description"] == "My repo desc"


def test_project_detail_not_found(db_conn, mock_embedder):
    store = Store(db_conn)
    retriever = Retriever(store, mock_embedder)
    assert retriever.project_detail("nope/nope") is None


def test_db_status(db_conn, mock_embedder):
    store = Store(db_conn)
    retriever = Retriever(store, mock_embedder)

    _add_project(store, mock_embedder, "a", "b", "desc", language="Python")
    _add_project(store, mock_embedder, "c", "d", "desc", language="Python")
    _add_project(store, mock_embedder, "e", "f", "desc", language="Go")

    status = retriever.db_status()
    assert status["total_projects"] == 3
    assert status["indexed_projects"] == 3
    assert status["top_languages"]["Python"] == 2


def test_readme_excerpt_limited(db_conn, mock_embedder):
    store = Store(db_conn)
    retriever = Retriever(store, mock_embedder)

    p = Project.from_dict({
        "owner": "long", "name": "readme",
        "description": "test", "stars": 100,
        "readme": "x" * 2000,
    })
    pid = store.insert_or_update(p)
    store.insert_vector(pid, mock_embedder.encode("test"))

    results = retriever.search("test", k=5)
    assert len(results[0]["readme_excerpt"]) <= 500
