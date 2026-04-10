"""SQLite storage layer with vector search support."""

from __future__ import annotations

import json
import sqlite3

from one_plus_one.models import Project


class Store:
    """Manages project persistence and vector indexing."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_or_update(self, project: Project) -> int:
        """Insert or update a project. Returns project id."""
        cur = self.conn.execute(
            """INSERT INTO projects (owner, name, full_name, description, url, stars,
               language, topics, readme, crawled_at, updated_at, quality_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(full_name) DO UPDATE SET
                   description=excluded.description,
                   url=excluded.url,
                   stars=excluded.stars,
                   language=excluded.language,
                   topics=excluded.topics,
                   readme=excluded.readme,
                   updated_at=excluded.updated_at
               RETURNING id""",
            (
                project.owner,
                project.name,
                project.full_name,
                project.description,
                project.url,
                project.stars,
                project.language,
                json.dumps(project.topics),
                project.readme,
                project.crawled_at,
                project.updated_at,
                project.quality_score,
            ),
        )
        row = cur.fetchone()
        self.conn.commit()
        return row[0]

    def insert_vector(self, project_id: int, embedding: list[float]) -> None:
        """Store embedding vector for a project.

        Uses sqlite-vec. If a vector already exists for this project_id,
        it is replaced.
        """
        import sqlite_vec
        packed = sqlite_vec.serialize_float32(embedding)

        # Delete existing if any (vec0 doesn't support UPDATE)
        self.conn.execute(
            "DELETE FROM project_vectors WHERE rowid = ?", (project_id,)
        )
        self.conn.execute(
            "INSERT INTO project_vectors(rowid, emb) VALUES (?, ?)",
            (project_id, packed),
        )
        self.conn.commit()

    def exists(self, full_name: str) -> bool:
        """Check if a project already exists in the database."""
        cur = self.conn.execute(
            "SELECT 1 FROM projects WHERE full_name = ?", (full_name,)
        )
        return cur.fetchone() is not None

    def get_by_id(self, project_id: int) -> Project | None:
        """Fetch a project by ID."""
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_project(row)

    def count(self) -> int:
        """Return total number of projects."""
        return self.conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

    def get_unindexed(self, limit: int = 100) -> list[dict]:
        """Get projects that don't have a vector yet."""
        columns = ["id", "owner", "name", "full_name", "description", "url",
                   "stars", "language", "topics", "readme", "crawled_at",
                   "updated_at", "quality_score"]
        rows = self.conn.execute(
            """SELECT p.* FROM projects p
               LEFT JOIN project_vectors v ON v.rowid = p.id
               WHERE v.rowid IS NULL
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [{columns[i]: r[i] for i in range(len(columns))} for r in rows]

    @staticmethod
    def _row_to_project(row) -> Project:
        """Convert a DB row to Project."""
        return Project(
            id=row[0],
            owner=row[1],
            name=row[2],
            description=row[4],
            url=row[5],
            stars=row[6],
            language=row[7],
            topics=json.loads(row[8]) if row[8] else [],
            readme=row[9],
            crawled_at=row[10],
            updated_at=row[11],
            quality_score=row[12],
        )
