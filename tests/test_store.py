"""Tests for the storage layer."""

import json

from one_plus_one.models import Project
from one_plus_one.store import Store


def test_insert_and_retrieve(db_conn):
    store = Store(db_conn)
    project = Project.from_dict({
        "owner": "test", "name": "repo",
        "description": "A repo", "stars": 100,
    })
    pid = store.insert_or_update(project)
    assert pid > 0

    fetched = store.get_by_id(pid)
    assert fetched is not None
    assert fetched.name == "repo"
    assert fetched.stars == 100


def test_upsert(db_conn):
    store = Store(db_conn)
    p = Project.from_dict({"owner": "a", "name": "b", "stars": 10})
    pid1 = store.insert_or_update(p)

    p2 = Project.from_dict({"owner": "a", "name": "b", "stars": 20})
    pid2 = store.insert_or_update(p2)

    assert pid1 == pid2  # Same project, same ID
    assert store.get_by_id(pid1).stars == 20


def test_exists(db_conn):
    store = Store(db_conn)
    store.insert_or_update(Project.from_dict({"owner": "x", "name": "y"}))
    assert store.exists("x/y")
    assert not store.exists("nope/nah")


def test_count(db_conn):
    store = Store(db_conn)
    assert store.count() == 0
    store.insert_or_update(Project.from_dict({"owner": "a", "name": "b"}))
    store.insert_or_update(Project.from_dict({"owner": "c", "name": "d"}))
    assert store.count() == 2


def test_insert_vector(db_conn, mock_embedder):
    store = Store(db_conn)
    p = Project.from_dict({"owner": "vec", "name": "test"})
    pid = store.insert_or_update(p)

    vec = mock_embedder.encode("test vector")
    store.insert_vector(pid, vec)

    # Verify vector exists via direct query
    cur = db_conn.execute("SELECT rowid FROM project_vectors WHERE rowid = ?", (pid,))
    assert cur.fetchone() is not None


def test_get_unindexed(db_conn):
    store = Store(db_conn)
    store.insert_or_update(Project.from_dict({"owner": "a", "name": "b"}))
    store.insert_or_update(Project.from_dict({"owner": "c", "name": "d"}))

    unindexed = store.get_unindexed(limit=10)
    assert len(unindexed) == 2
