"""Tests for trending page parser."""

from one_plus_one.crawler.trending import parse_trending_page


TRENDING_HTML = """
<html>
<body>
<article class="Box-row">
    <h2 class="h3 lh-condensed">
        <a href="/nousresearch/hermes-agent">
            nousresearch / hermes-agent
        </a>
    </h2>
    <p class="col-9 color-fg-muted my-1 pr-4">
        A multi-agent framework for AI research
    </p>
    <a href="/nousresearch/hermes-agent/stargazers">
        1,234
    </a>
</article>
<article class="Box-row">
    <h2 class="h3 lh-condensed">
        <a href="/some-org/some-repo">
            some-org / some-repo
        </a>
    </h2>
    <p class="col-9 color-fg-muted my-1 pr-4">
        Another cool project
    </p>
    <a href="/some-org/some-repo/stargazers">
        567
    </a>
</article>
</body>
</html>
"""


def test_parse_trending_basic():
    results = parse_trending_page(TRENDING_HTML)
    assert len(results) == 2

    assert results[0]["owner"] == "nousresearch"
    assert results[0]["name"] == "hermes-agent"
    assert "multi-agent" in results[0]["description"]
    assert results[0]["stars"] == 1234

    assert results[1]["owner"] == "some-org"
    assert results[1]["stars"] == 567


def test_parse_empty_page():
    results = parse_trending_page("<html><body></body></html>")
    assert results == []


def test_parse_malformed_row():
    html_content = """
    <article class="Box-row">
        <h2><a href="/incomplete">missing second part</a></h2>
    </article>
    <article class="Box-row">
        <h2><a href="/valid/repo">valid / repo</a></h2>
        <p class="col-9 color-fg-muted my-1 pr-4">desc</p>
        <a href="/valid/repo/stargazers">100</a>
    </article>
    """
    results = parse_trending_page(html_content)
    assert len(results) == 1
    assert results[0]["name"] == "repo"
