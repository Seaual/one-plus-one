"""Semantic search retriever for finding related projects."""

from __future__ import annotations

import json
import sqlite3

from one_plus_one.embedder import Embedder
from one_plus_one.store import Store


class Retriever:
    """Searches for projects semantically related to a query."""

    def __init__(self, store: Store, embedder: Embedder):
        self.store = store
        self.embedder = embedder

    def search(
        self,
        query: str,
        k: int = 20,
        language: str | None = None,
        min_stars: int | None = None,
    ) -> list[dict]:
        """Search for projects related to the query.

        Returns list of project cards:
        {id, owner, name, description, stars, url, language, topics, readme_excerpt}
        """
        import sqlite_vec
        query_vec = self.embedder.encode(query)
        packed = sqlite_vec.serialize_float32(query_vec)

        # Build the vector search query
        vector_sql = """
            SELECT v.rowid, v.distance
            FROM project_vectors v
            WHERE v.emb MATCH ?
            ORDER BY v.distance
            LIMIT ?
        """

        # Get top candidates from vector search
        rows = self.store.conn.execute(
            vector_sql, (packed, k)
        ).fetchall()

        if not rows:
            return []

        # Get full project data
        ids = [r[0] for r in rows]
        placeholders = ",".join("?" * len(ids))

        where = f"p.id IN ({placeholders})"
        params: list = list(ids)

        if language:
            where += " AND p.language = ?"
            params.append(language)
        if min_stars:
            where += " AND p.stars >= ?"
            params.append(min_stars)

        sql = f"""
            SELECT p.id, p.owner, p.name, p.full_name, p.description,
                   p.url, p.stars, p.language, p.topics, p.readme,
                   p.quality_score
            FROM projects p
            WHERE {where}
            ORDER BY p.stars DESC
        """

        results = []
        for row in self.store.conn.execute(sql, params).fetchall():
            results.append({
                "id": row[0],
                "owner": row[1],
                "name": row[2],
                "full_name": row[3],
                "description": row[4],
                "url": row[5],
                "stars": row[6],
                "language": row[7],
                "topics": json.loads(row[8]) if row[8] else [],
                "readme_excerpt": (row[9] or "")[:500],
                "quality_score": row[10],
            })

        return results

    def project_detail(self, full_name: str) -> dict | None:
        """Get full details of a specific project."""
        row = self.store.conn.execute(
            "SELECT * FROM projects WHERE full_name = ?", (full_name,)
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "owner": row[1],
            "name": row[2],
            "full_name": row[3],
            "description": row[4],
            "url": row[5],
            "stars": row[6],
            "language": row[7],
            "topics": json.loads(row[8]) if row[8] else [],
            "readme": row[9],
            "quality_score": row[12],
        }

    def db_status(self) -> dict:
        """Return database statistics."""
        total = self.store.count()
        has_vector = self.store.conn.execute(
            "SELECT COUNT(DISTINCT rowid) FROM project_vectors"
        ).fetchone()[0]
        lang_counts = {}
        for row in self.store.conn.execute(
            "SELECT language, COUNT(*) FROM projects WHERE language != '' GROUP BY language ORDER BY COUNT(*) DESC LIMIT 10"
        ).fetchall():
            lang_counts[row[0]] = row[1]
        return {
            "total_projects": total,
            "indexed_projects": has_vector,
            "top_languages": lang_counts,
        }
