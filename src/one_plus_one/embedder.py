"""Embedding model wrapper using BAAI/bge-m3 via sentence-transformers."""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    """Abstract interface for embedding models."""

    def encode(self, text: str) -> list[float]: ...


class BgeM3Embedder:
    """BAAI/bge-m3 embedding model via sentence-transformers.

    Produces 1024-dimensional dense vectors.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", device: str = "cpu"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(
            model_name,
            device=device,
            trust_remote_code=True,
        )

    def encode(self, text: str) -> list[float]:
        """Encode text into a 1024-dim float vector."""
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode multiple texts at once."""
        vecs = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]


def prepare_embed_text(project: dict) -> str:
    """Combine project fields into a single string for embedding.

    Uses README (first 4000 chars) + description + topics.
    """
    readme = (project.get("readme") or "")[:4000]
    desc = project.get("description") or ""
    topics = " ".join(project.get("topics", []) or [])
    return f"{desc}\n{topics}\n{readme}"
