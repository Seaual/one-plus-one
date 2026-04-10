"""Daily report generation for one-plus-one.

Generates a concise Telegram-friendly report of top new/high-quality projects.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from one_plus_one.store import Store
from one_plus_one.assessor import CompetitionAssessor
from one_plus_one.quality import QualityScorer


def generate_daily_report(conn: sqlite3.Connection, top_k: int = 10) -> str:
    """Generate a daily report string.

    Args:
        conn: DB connection.
        top_k: Number of projects to feature.

    Returns:
        A formatted Markdown string ready for Telegram.
    """
    store = Store(conn)
    
    # Fetch top projects by quality score
    top_projects = store.get_top_projects(limit=top_k)
    
    # Assess competition for the top ones
    report_lines = [
        "🚀 **One+One Daily Report**",
        f"📅 {datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]
    
    if not top_projects:
        report_lines.append("⚠️ 数据库中暂无项目，请先运行 `crawl_trending` 或 `crawl_topic`。")
        return "\n".join(report_lines)
        
    for i, p in enumerate(top_projects, 1):
        stars = f"⭐ {p['stars']:,}" if p.get('stars') else "⭐ N/A"
        lang = f" [{p['language']}]" if p.get('language') else ""
        quality = f"Quality: {p.get('quality_score', 0):.0f}/100"
        
        report_lines.append(
            f"**{i}. {p['full_name']}** ({stars}){lang}\n"
            f"_{p.get('description', 'No description')}_\n"
            f"🔗 {p['url']}\n"
            f"📊 {quality}"
        )
        report_lines.append("")
        
    # Add a "Trend Summary" section based on ALL projects
    import json
    all_projects = store.get_top_projects(limit=500)
    topic_counts: dict[str, int] = {}
    for p in all_projects:
        topics = json.loads(p.get("topics", "[]")) if isinstance(p.get("topics"), str) else (p.get("topics") or [])
        for t in topics:
            topic_counts[t] = topic_counts.get(t, 0) + 1
            
    if topic_counts:
        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        report_lines.append("🔥 **本周热门技术趋势:**")
        for t, c in top_topics:
            report_lines.append(f"  • `{t}` ({c} 个项目)")
            
    return "\n".join(report_lines)
