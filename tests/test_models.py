"""Tests for data models and DB initialization."""

import sqlite3

import pytest
import sqlite_vec

from one_plus_one.models import Project, init_db


class TestProject:
    def test_from_dict_minimal(self):
        data = {"owner": "test", "name": "repo"}
        p = Project.from_dict(data)
        assert p.owner == "test"
        assert p.name == "repo"
        assert p.full_name == "test/repo"
        assert p.stars == 0
        assert p.topics == []

    def test_from_dict_full(self):
        data = {
            "owner": "nous",
            "name": "hermes",
            "description": "An AI agent",
            "stars": 1000,
            "language": "Python",
            "topics": ["ai", "agent"],
            "readme": "# Hermes\n\n...",
        }
        p = Project.from_dict(data)
        assert p.description == "An AI agent"
        assert p.stars == 1000
        assert p.topics == ["ai", "agent"]
        assert "# Hermes" in p.readme

    def test_to_dict_roundtrip(self):
        p = Project.from_dict({"owner": "a", "name": "b", "stars": 42})
        d = p.to_dict()
        assert d["owner"] == "a"
        assert d["stars"] == 42


class TestInitDB:
    def test_creates_projects_table(self, db_conn):
        cur = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
        )
        assert cur.fetchone() is not None

    def test_creates_project_vectors_table(self, db_conn):
        cur = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE name='project_vectors'"
        )
        assert cur.fetchone() is not None

    def test_creates_crawl_jobs_table(self, db_conn):
        cur = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='crawl_jobs'"
        )
        assert cur.fetchone() is not None

    def test_insert_and_query_project(self, db_conn):
        db_conn.execute(
            """INSERT INTO projects (owner, name, full_name, url, stars, crawled_at, updated_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            ("test", "repo", "test/repo", "https://github.com/test/repo", 100),
        )
        db_conn.commit()
        row = db_conn.execute("SELECT * FROM projects").fetchone()
        assert row[1] == "test"
        assert row[2] == "repo"
        assert row[6] == 100

    def test_unique_full_name(self, db_conn):
        db_conn.execute(
            """INSERT INTO projects (owner, name, full_name, url, crawled_at, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
            ("test", "repo", "test/repo", "https://github.com/test/repo"),
        )
        db_conn.commit()
        with pytest.raises(Exception):  # UNIQUE constraint
            db_conn.execute(
                """INSERT INTO projects (owner, name, full_name, url, crawled_at, updated_at)
                   VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
                ("test", "repo", "test/repo", "https://github.com/test/repo2"),
            )
