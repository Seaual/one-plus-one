"""Parse GitHub trending page HTML into structured repo data.

Full implementation will be done in Task 3.
This stub handles the minimal HTML pattern needed by tests.
"""

from __future__ import annotations


def parse_trending_page(html: str) -> list[dict]:
    """Parse GitHub trending page and return list of repo dicts.

    Extracts repo name, description, and stars from article.Box-row elements.
    """
    results: list[dict] = []

    # Split into individual row blocks
    rows = html.split('<article class="Box-row">')

    for row in rows[1:]:  # skip first split fragment
        # Extract repo path from <h2><a href="/owner/name">
        repo_path = ""
        start = row.find('<a href="/')
        if start != -1:
            end = row.find('"', start + 10)
            if end != -1:
                repo_path = row[start + 10:end].strip("/")

        # Extract description from <p> tag
        desc = ""
        p_start = row.find("<p>")
        if p_start != -1:
            p_end = row.find("</p>", p_start)
            if p_end != -1:
                desc = row[p_start + 3:p_end].strip()

        # Extract stars count
        stars = 0
        stars_marker = '<span class="d-inline-block float-sm-right">'
        s_start = row.find(stars_marker)
        if s_start != -1:
            s_start += len(stars_marker)
            s_end = row.find("</span>", s_start)
            if s_end != -1:
                stars_text = row[s_start:s_end].strip().replace(",", "")
                try:
                    stars = int(stars_text)
                except ValueError:
                    stars = 0

        if repo_path:
            parts = repo_path.split("/")
            owner = parts[0] if len(parts) >= 1 else ""
            name = parts[1] if len(parts) >= 2 else ""
            results.append({
                "owner": owner,
                "name": name,
                "description": desc,
                "stars": stars,
                "language": "",
                "topics": [],
                "url": f"https://github.com/{repo_path}",
            })

    return results
