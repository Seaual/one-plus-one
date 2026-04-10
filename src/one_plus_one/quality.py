"""Quality scoring for GitHub projects."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class QualityScorer:
    """Computes a 0-100 quality score for a project.

    Scoring rubric:
    - Has README: +20
    - README > 1000 chars: +20
    - stars > 100: +20
    - Has topics: +10
    - Has description: +10
    - Recent update (within 30 days): +10

    Total: 100 (capped)
    """

    RUBRIC = {
        "has_readme": 20,
        "long_readme": 20,
        "stars_100": 20,
        "has_topics": 10,
        "has_description": 10,
        "recent_update": 10,
    }

    @classmethod
    def score(cls, project: dict) -> int:
        """Compute quality score (0-100) for a project dict."""
        return cls.breakdown(project)["total"]

    @classmethod
    def breakdown(cls, project: dict) -> dict[str, int]:
        """Return individual score components."""
        readme = project.get("readme") or ""
        stars = project.get("stars", 0) or 0
        topics = project.get("topics") or []
        desc = project.get("description") or ""
        crawled_at = project.get("crawled_at") or ""

        scores: dict[str, int] = {}
        scores["has_readme"] = cls.RUBRIC["has_readme"] if readme.strip() else 0
        scores["long_readme"] = cls.RUBRIC["long_readme"] if len(readme) > 1000 else 0
        scores["stars_100"] = cls.RUBRIC["stars_100"] if stars > 100 else 0
        scores["has_topics"] = cls.RUBRIC["has_topics"] if topics else 0
        scores["has_description"] = cls.RUBRIC["has_description"] if desc.strip() else 0
        scores["recent_update"] = cls._check_recent_update(crawled_at)

        scores["total"] = min(sum(scores.values()), 100)
        return scores

    @classmethod
    def _check_recent_update(cls, crawled_at: str) -> int:
        """Check if project was updated within last 30 days."""
        if not crawled_at:
            return 0
        try:
            updated = datetime.fromisoformat(crawled_at)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            return cls.RUBRIC["recent_update"] if updated > cutoff else 0
        except (ValueError, TypeError):
            return 0
