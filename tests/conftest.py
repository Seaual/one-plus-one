"""Shared test fixtures."""

import sqlite3
from unittest.mock import MagicMock

import pytest

from one_plus_one.models import init_db


@pytest.fixture
def db_conn():
    """In-memory SQLite database with extensions loaded."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def mock_embedder():
    """Mock embedder that returns deterministic fake vectors."""
    m = MagicMock()
    def fake_encode(text: str) -> list[float]:
        # Deterministic fake: hash-based
        import hashlib
        h = hashlib.md5(text.encode()).digest()
        return [float(b) / 255.0 for b in h] * 64  # 1024 dims
    m.encode.side_effect = fake_encode
    return m
