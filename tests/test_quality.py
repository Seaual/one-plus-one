"""Tests for quality scoring."""

from one_plus_one.quality import QualityScorer


def _make_project(**kwargs):
    """Helper: create project metadata dict with defaults."""
    defaults = {
        "readme": "",
        "stars": 0,
        "topics": [],
        "description": "",
        "crawled_at": "2026-01-01T00:00:00",
    }
    defaults.update(kwargs)
    return defaults


class TestQualityScorer:
    def test_empty_project_is_zero(self):
        p = _make_project()
        assert QualityScorer.score(p) == 0

    def test_has_readme(self):
        p = _make_project(readme="# Hello\nSome content here")
        assert QualityScorer.score(p) == 20

    def test_long_readme(self):
        p = _make_project(readme="x" * 1500)
        assert QualityScorer.score(p) == 40  # 20 + 20

    def test_high_stars(self):
        p = _make_project(stars=500)
        assert QualityScorer.score(p) == 20

    def test_has_topics(self):
        p = _make_project(topics=["ai", "ml", "python"])
        assert QualityScorer.score(p) == 10

    def test_has_description(self):
        p = _make_project(description="A cool project")
        assert QualityScorer.score(p) == 10

    def test_full_score(self):
        """All conditions met = 90 (rubric max)."""
        p = _make_project(
            readme="x" * 1500,
            stars=1000,
            topics=["ai", "ml"],
            description="An AI/ML project",
            crawled_at="2026-04-09T00:00:00",  # recent
        )
        assert QualityScorer.score(p) == 90

    def test_recent_update(self):
        """Project updated within last 30 days gets +10."""
        p = _make_project(
            readme="x" * 100,
            crawled_at="2026-04-09T00:00:00",  # recent (within 30 days)
        )
        assert QualityScorer.score(p) == 20 + 10  # readme(20) + recent(10)

    def test_not_recent(self):
        """Project older than 30 days doesn't get recency bonus."""
        p = _make_project(
            readme="x" * 100,
            crawled_at="2025-01-01T00:00:00",  # old
        )
        assert QualityScorer.score(p) == 20  # readme only

    def test_score_capped_at_100(self):
        """Score never exceeds 100."""
        p = _make_project(
            readme="x" * 5000,
            stars=100000,
            topics=["a", "b", "c"],
            description="desc",
            crawled_at="2026-04-09T00:00:00",
        )
        assert QualityScorer.score(p) <= 100

    def test_breakdown(self):
        """Breakdown returns individual scores."""
        p = _make_project(
            readme="x" * 1500,
            stars=500,
            topics=["ai"],
            description="An AI project",
            crawled_at="2026-04-09T00:00:00",
        )
        breakdown = QualityScorer.breakdown(p)
        assert breakdown["has_readme"] == 20
        assert breakdown["long_readme"] == 20
        assert breakdown["stars_100"] == 20
        assert breakdown["has_topics"] == 10
        assert breakdown["has_description"] == 10
        assert breakdown["recent_update"] == 10
        assert breakdown["total"] == 90
