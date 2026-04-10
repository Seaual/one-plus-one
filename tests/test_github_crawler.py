"""Tests for GitHub API crawler."""

import pytest

from one_plus_one.crawler.github import GitHubClient
from one_plus_one.models import Project


@pytest.fixture
def client():
    return GitHubClient()


@pytest.mark.asyncio
async def test_fetch_repo_success(client, httpx_mock):
    """Test fetching a single repo with mock responses."""
    httpx_mock.add_response(
        url="https://api.github.com/repos/test/repo",
        json={
            "description": "A test repo",
            "html_url": "https://github.com/test/repo",
            "stargazers_count": 42,
            "language": "Python",
            "topics": ["test", "demo"],
        },
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/test/repo/readme",
        json={"content": "IyBUZXN0\n"},  # "# Test" base64
    )

    project = await client.fetch_repo("test", "repo")
    assert project is not None
    assert project.owner == "test"
    assert project.name == "repo"
    assert project.description == "A test repo"
    assert project.stars == 42
    assert project.language == "Python"
    assert project.topics == ["test", "demo"]
    assert "# Test" in project.readme


@pytest.mark.asyncio
async def test_fetch_repo_not_found(client, httpx_mock):
    httpx_mock.add_response(
        url="https://api.github.com/repos/test/nope",
        status_code=403,
        json={"message": "Not Found"},
    )
    result = await client.fetch_repo("test", "nope")
    assert result is None


@pytest.mark.asyncio
async def test_fetch_trending_fallback(client, httpx_mock):
    """Test trending fallback with mock HTML."""
    # Search API fails
    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=created%3A%3E2026-04-09&sort=stars&order=desc&per_page=30",
        status_code=403,
    )
    # Trending page mock
    html = """
    <article class="Box-row">
        <h2><a href="/user/repo">user/repo</a></h2>
        <p>A cool project</p>
        <span class="d-inline-block float-sm-right">420</span>
    </article>
    """
    httpx_mock.add_response(
        url="https://github.com/trending?since=daily",
        text=html,
    )
    results = await client.fetch_trending_repos("daily")
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_fetch_by_topic(client, httpx_mock):
    httpx_mock.add_response(
        url="https://api.github.com/search/repositories?q=topic%3Aai&sort=stars&order=desc&per_page=50",
        json={
            "items": [
                {
                    "owner": {"login": "ai-org"},
                    "name": "cool-ai",
                    "description": "Cool AI project",
                    "stargazers_count": 10000,
                    "language": "Python",
                    "topics": ["ai", "ml"],
                    "html_url": "https://github.com/ai-org/cool-ai",
                }
            ]
        },
    )
    results = await client.fetch_by_topic("ai", limit=50)
    assert len(results) == 1
    assert results[0]["owner"] == "ai-org"
    assert results[0]["stars"] == 10000
