"""Parse GitHub trending page HTML into structured data."""

from __future__ import annotations

from lxml import html


def parse_trending_page(html_content: str) -> list[dict]:
    """Parse github.com/trending HTML into a list of repo dicts.

    Each dict: {owner, name, description, stars, url}
    """
    tree = html.fromstring(html_content)
    rows = tree.xpath('//article[@class="Box-row"]')

    results = []
    for row in rows:
        # Repo link: /owner/name
        link_el = row.xpath('.//h2/a[@href]')
        if not link_el:
            continue
        href = link_el[0].get("href", "").strip("/")
        parts = href.split("/")
        if len(parts) != 2:
            continue
        owner, name = parts

        # Description
        desc_els = row.xpath(".//p[@class='col-9 color-fg-muted my-1 pr-4']")
        description = desc_els[0].text_content().strip() if desc_els else ""

        # Stars (text like "4,200 stars this week")
        star_els = row.xpath('.//a[contains(@href, "/stargazers")]')
        stars_text = star_els[0].text_content().strip() if star_els else "0"
        stars = int(stars_text.replace(",", "").split()[0]) if stars_text else 0

        results.append({
            "owner": owner,
            "name": name,
            "description": description,
            "stars": stars,
            "url": f"https://github.com/{owner}/{name}",
        })

    return results
