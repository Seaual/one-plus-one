"""Tests for competition assessor."""

from one_plus_one.assessor import CompetitionAssessor


class TestCompetitionAssessor:
    def test_empty_db(self):
        report = CompetitionAssessor.assess([], "AI tool")
        assert report["query"] == "AI tool"
        assert report["total_related"] == 0
        assert report["verdict"] == "无人区"

    def test_low_competition(self):
        projects = [
            {"full_name": "a/repo", "stars": 50, "crawled_at": "2026-04-09T00:00:00"},
            {"full_name": "b/repo", "stars": 30, "crawled_at": "2026-04-08T00:00:00"},
        ]
        report = CompetitionAssessor.assess(projects, "small tool")
        assert report["total_related"] == 2
        assert report["top_10_avg_stars"] == 40
        assert report["recent_30d_count"] == 2
        assert report["verdict"] == "蓝海"

    def test_high_competition(self):
        projects = [
            {"full_name": f"org/repo{i}", "stars": 10000 + i * 100, "crawled_at": "2026-04-09T00:00:00"}
            for i in range(15)
        ]
        report = CompetitionAssessor.assess(projects, "popular framework")
        assert report["total_related"] == 15
        assert report["top_10_avg_stars"] > 10000
        assert report["verdict"] == "红海"

    def test_medium_competition(self):
        projects = [
            {"full_name": f"x/repo{i}", "stars": 500 + i * 50, "crawled_at": "2026-04-01T00:00:00"}
            for i in range(8)
        ]
        report = CompetitionAssessor.assess(projects, "medium tool")
        assert report["total_related"] == 8
        assert report["top_10_avg_stars"] > 0
        assert report["verdict"] == "中等竞争"

    def test_verdict_thresholds(self):
        """Verify verdict classification logic."""
        # 无人区: 0 projects
        assert CompetitionAssessor.assess([], "x")["verdict"] == "无人区"
        # 蓝海: < 5 projects AND avg_stars < 500
        low = [{"full_name": "a/b", "stars": 100, "crawled_at": "2026-01-01"}]
        assert CompetitionAssessor.assess(low, "x")["verdict"] == "蓝海"
        # 红海: > 10 projects OR avg_stars > 5000
        high = [{"full_name": f"r/r{i}", "stars": 10000, "crawled_at": "2026-01-01"} for i in range(12)]
        assert CompetitionAssessor.assess(high, "x")["verdict"] == "红海"
        # 中等竞争: everything else
        med = [{"full_name": f"m/m{i}", "stars": 800, "crawled_at": "2026-01-01"} for i in range(6)]
        assert CompetitionAssessor.assess(med, "x")["verdict"] == "中等竞争"

    def test_report_has_all_fields(self):
        projects = [{"full_name": "a/b", "stars": 200, "crawled_at": "2026-04-09"}]
        report = CompetitionAssessor.assess(projects, "test")
        for key in ["query", "total_related", "top_10_avg_stars", "recent_30d_count", "verdict", "summary"]:
            assert key in report
