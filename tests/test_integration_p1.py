"""Integration tests for P1 features."""

import sqlite3

import sqlite_vec

from one_plus_one.models import init_db, Project
from one_plus_one.store import Store
from one_plus_one.retriever import Retriever
from one_plus_one.synthesizer import Synthesizer
from one_plus_one.assessor import CompetitionAssessor
from one_plus_one.quality import QualityScorer


def _setup_db():
    conn = sqlite3.connect(":memory:")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    init_db(conn)
    return conn


def _add_project(store, embedder, owner, name, desc, stars=100, language="Python", readme=""):
    p = Project.from_dict({
        "owner": owner, "name": name,
        "description": desc, "stars": stars, "language": language,
        "readme": readme,
    })
    pid = store.insert_or_update(p)
    vec = embedder.encode(desc)
    store.insert_vector(pid, vec)
    return pid


def test_quality_auto_computed(mock_embedder):
    """Quality score is auto-computed on insert."""
    conn = _setup_db()
    store = Store(conn)

    # Low quality project (gets +10 for recent_update since crawled_at is auto-set)
    _add_project(store, mock_embedder, "a", "empty", "", stars=0, readme="")
    row = store.conn.execute("SELECT quality_score FROM projects WHERE full_name = 'a/empty'").fetchone()
    assert row[0] == 10  # Only recent_update(+10), no readme/stars/topics/desc

    # High quality project
    _add_project(store, mock_embedder, "b", "full", "A great project",
                 stars=500, readme="# Readme\n" + "x" * 1200, language="Python")
    row = store.conn.execute("SELECT quality_score FROM projects WHERE full_name = 'b/full'").fetchone()
    # has_readme(20) + long_readme(20) + stars_100(20) + has_desc(10) = 70
    # (topics=[] so +0, no recency)
    assert row[0] >= 70

    conn.close()


def test_synthesize_from_db_projects(mock_embedder):
    """Synthesis works with projects stored in DB."""
    conn = _setup_db()
    store = Store(conn)

    _add_project(store, mock_embedder, "a", "ml-lib", "Machine learning framework",
                 stars=15000, readme="# ML-Lib\n\nFast ML framework.")
    _add_project(store, mock_embedder, "b", "viz-tool", "Interactive data visualization",
                 stars=8000, readme="# Viz-Tool\n\nCreate charts.")

    retriever = Retriever(store, mock_embedder)
    results = retriever.search("ML", k=5)

    assert len(results) >= 1

    # Synthesize from retrieval results
    if len(results) >= 2:
        report = Synthesizer.synthesize(results[0], results[1])
        assert report.combination_name
        assert report.one_liner
        assert len(report.to_markdown()) > 50

    conn.close()


def test_assess_competition_from_db(mock_embedder):
    """Competition assessment works with DB projects."""
    conn = _setup_db()
    store = Store(conn)

    _add_project(store, mock_embedder, "a", "ai1", "AI tool", stars=5000)
    _add_project(store, mock_embedder, "b", "ai2", "AI platform", stars=3000)
    _add_project(store, mock_embedder, "c", "ai3", "AI assistant", stars=2000)

    retriever = Retriever(store, mock_embedder)
    candidates = retriever.search("AI", k=10)

    report = CompetitionAssessor.assess(candidates, "AI tool")
    assert report["total_related"] == 3
    assert report["top_10_avg_stars"] > 0
    assert report["verdict"] in ["蓝海", "中等竞争", "红海", "无人区"]

    conn.close()
