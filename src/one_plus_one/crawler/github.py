"""GitHub API client for fetching repository metadata."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from one_plus_one.models import Project


@dataclass
class GitHubClient:
    """Async GitHub API client with rate limit handling."""

    token: str | None = None
    base_url: str = "https://api.github.com"
    _client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Accept": "application/vnd.github+json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def fetch_repo(self, owner: str, name: str) -> Project | None:
        """Fetch a single repository's metadata and README."""
        try:
            repo_resp = await self.client.get(f"/repos/{owner}/{name}")
            if repo_resp.status_code == 404:
                return None
            repo_resp.raise_for_status()
            repo = repo_resp.json()

            readme_resp = await self.client.get(f"/repos/{owner}/{name}/readme")
            readme = ""
            if readme_resp.status_code == 200:
                data = readme_resp.json()
                readme = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

            return Project(
                owner=owner,
                name=name,
                description=repo.get("description") or "",
                url=repo.get("html_url", f"https://github.com/{owner}/{name}"),
                stars=repo.get("stargazers_count", 0),
                language=repo.get("language") or "",
                topics=repo.get("topics", []) or [],
                readme=readme,
            )
        except httpx.HTTPError:
            return None

    async def fetch_trending_repos(self, since: str = "daily") -> list[dict]:
        """Fetch trending repos via GitHub search API.

        Falls back to trending page parsing if search fails.
        """
        from one_plus_one.crawler.trending import parse_trending_page

        try:
            days = {"daily": 1, "weekly": 7, "monthly": 30}.get(since, 1)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

            resp = await self.client.get(
                "/search/repositories",
                params={
                    "q": f"created:>{cutoff}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 30,
                },
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                return [
                    {
                        "owner": item["owner"]["login"],
                        "name": item["name"],
                        "description": item.get("description") or "",
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language") or "",
                        "topics": item.get("topics", []) or [],
                        "url": item.get("html_url", ""),
                    }
                    for item in items
                ]
        except httpx.HTTPError:
            pass

        # Fallback: parse trending page
        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                html_resp = await c.get(
                    f"https://github.com/trending?since={since}"
                )
                if html_resp.status_code == 200:
                    return parse_trending_page(html_resp.text)
        except httpx.HTTPError:
            pass

        return []

    async def fetch_by_topic(self, topic: str, limit: int = 50) -> list[dict]:
        """Search repos by topic, sorted by stars."""
        try:
            resp = await self.client.get(
                "/search/repositories",
                params={
                    "q": f"topic:{topic}",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": min(limit, 100),
                },
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                return [
                    {
                        "owner": item["owner"]["login"],
                        "name": item["name"],
                        "description": item.get("description") or "",
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language") or "",
                        "topics": item.get("topics", []) or [],
                        "url": item.get("html_url", ""),
                    }
                    for item in items[:limit]
                ]
        except httpx.HTTPError:
            pass
        return []

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
