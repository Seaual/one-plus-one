"""Tests for embedder module."""

import hashlib

from one_plus_one.embedder import BgeM3Embedder, prepare_embed_text


class TestPrepareEmbedText:
    def test_combines_all_fields(self):
        project = {
            "description": "A test project",
            "topics": ["ai", "python"],
            "readme": "# Hello\n\nThis is the readme.",
        }
        text = prepare_embed_text(project)
        assert "A test project" in text
        assert "ai python" in text
        assert "# Hello" in text

    def test_truncates_long_readme(self):
        project = {"readme": "x" * 8000, "description": "", "topics": []}
        text = prepare_embed_text(project)
        assert len(text) <= 4000 + 2  # 4000 + 2 newlines between fields

    def test_handles_none_fields(self):
        project = {"description": None, "topics": None, "readme": None}
        text = prepare_embed_text(project)
        assert isinstance(text, str)

    def test_hash_deterministic(self):
        project = {"description": "same", "topics": ["a"], "readme": "content"}
        t1 = prepare_embed_text(project)
        t2 = prepare_embed_text(project)
        assert t1 == t2


class TestMockEmbedder:
    """Test using the mock embedder from conftest (no real model)."""

    def test_mock_produces_1024_dim(self, mock_embedder):
        vec = mock_embedder.encode("test")
        assert len(vec) == 1024

    def test_mock_deterministic(self, mock_embedder):
        v1 = mock_embedder.encode("hello")
        v2 = mock_embedder.encode("hello")
        assert v1 == v2

    def test_mock_different_inputs(self, mock_embedder):
        v1 = mock_embedder.encode("hello")
        v2 = mock_embedder.encode("world")
        assert v1 != v2
