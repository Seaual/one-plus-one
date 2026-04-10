"""Data models and database initialization."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Project:
    """A GitHub project with README-level metadata."""

    owner: str
    name: str
    description: str = ""
    url: str = ""
    stars: int = 0
    language: str = ""
    topics: list[str] = field(default_factory=list)
    readme: str = ""
    crawled_at: str = ""
    updated_at: str = ""
    quality_score: float = 0.0
    id: int | None = None

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            owner=data["owner"],
            name=data["name"],
            description=data.get("description", ""),
            url=data.get("url", f"https://github.com/{data['owner']}/{data['name']}"),
            stars=data.get("stars", 0),
            language=data.get("language", ""),
            topics=data.get("topics", []),
            readme=data.get("readme", ""),
            crawled_at=now,
            updated_at=now,
        )

    def to_dict(self) -> dict:
        return asdict(self)


def init_db(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist."""
    conn.enable_load_extension(True)
    import sqlite_vec
    sqlite_vec.load(conn)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            name TEXT NOT NULL,
            full_name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            stars INTEGER DEFAULT 0,
            language TEXT DEFAULT '',
            topics TEXT DEFAULT '[]',
            readme TEXT DEFAULT '',
            crawled_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            quality_score REAL DEFAULT 0.0
        );

        CREATE INDEX IF NOT EXISTS idx_projects_stars ON projects(stars DESC);
        CREATE INDEX IF NOT EXISTS idx_projects_language ON projects(language);

        CREATE TABLE IF NOT EXISTS crawl_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            projects_count INTEGER DEFAULT 0,
            started_at TEXT,
            finished_at TEXT
        );
    """)

    # Create vec table (vec0 syntax)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS project_vectors
        USING vec0(emb float[1024])
    """)
    conn.commit()
