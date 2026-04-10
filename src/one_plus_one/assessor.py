"""Competition assessment for project ideas."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


class CompetitionAssessor:
    """Evaluates market competition for a given query/domain."""

    @classmethod
    def assess(cls, projects: list[dict], query: str) -> dict:
        """Assess competition level based on retrieved projects.

        Args:
            projects: List of project dicts (from retriever.search results)
            query: The search query/domain being assessed

        Returns:
            Dict with: query, total_related, top_10_avg_stars,
                       recent_30d_count, verdict, summary
        """
        total = len(projects)

        # Top 10 average stars
        sorted_by_stars = sorted(projects, key=lambda p: p.get("stars", 0), reverse=True)
        top_10 = sorted_by_stars[:10]
        avg_stars = (
            sum(p.get("stars", 0) for p in top_10) / len(top_10)
            if top_10 else 0
        )

        # Recent 30-day count
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_count = 0
        for p in projects:
            crawled = p.get("crawled_at", "")
            if crawled:
                try:
                    dt = datetime.fromisoformat(crawled)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt > cutoff:
                        recent_count += 1
                except (ValueError, TypeError):
                    pass

        verdict = cls._classify(total, avg_stars)
        summary = cls._build_summary(query, total, avg_stars, recent_count, verdict)

        return {
            "query": query,
            "total_related": total,
            "top_10_avg_stars": round(avg_stars, 1),
            "recent_30d_count": recent_count,
            "verdict": verdict,
            "summary": summary,
        }

    @classmethod
    def _classify(cls, total: int, avg_stars: float) -> str:
        """Classify competition level."""
        if total == 0:
            return "无人区"
        if total > 10 or avg_stars > 5000:
            return "红海"
        if total < 5 and avg_stars < 500:
            return "蓝海"
        return "中等竞争"

    @classmethod
    def _build_summary(cls, query: str, total: int, avg_stars: float, recent: int, verdict: str) -> str:
        """Generate human-readable summary."""
        verdict_emoji = {"无人区": "🏜️", "蓝海": "🌊", "中等竞争": "⚖️", "红海": "🔴"}.get(verdict, "❓")
        lines = [
            f"{verdict_emoji} **竞争评估**: {verdict}",
            f"查询: {query}",
            f"相关项目: {total}",
            f"Top 10 平均 stars: {avg_stars:.0f}",
            f"近 30 天新增: {recent}",
        ]
        if verdict == "无人区":
            lines.append("💡 该领域暂无项目，属于创新机会")
        elif verdict == "蓝海":
            lines.append("💡 竞争较低，有差异化空间")
        elif verdict == "红海":
            lines.append("⚠️ 竞争激烈，需要显著差异化")
        else:
            lines.append("⚖️ 中等竞争，需要找到独特定位")
        return "\n".join(lines)
