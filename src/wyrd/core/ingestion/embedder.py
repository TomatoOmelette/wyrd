"""Embedding generation for text chunks."""

import os
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    """Protocol for embedding providers."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts."""
        ...

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...


class SentenceTransformerEmbedder:
    """Local embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedder.

        Args:
            model_name: Name of the sentence-transformer model to use.
                       Defaults to all-MiniLM-L6-v2 (fast, 384 dims).
                       Alternative: all-mpnet-base-v2 (better quality, 768 dims)
        """
        # Lazy import to avoid loading torch unless needed
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,
        )

        # Convert to list of lists for JSON serialization
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension


def get_embedder(
    provider: str | None = None,
    model: str | None = None,
) -> Embedder:
    """
    Get an embedder instance based on configuration.

    Args:
        provider: Embedding provider (local, openai, voyage). Defaults to env var or local.
        model: Model name. Defaults to env var or provider default.

    Returns:
        Embedder instance
    """
    provider = provider or os.environ.get("WYRD_EMBEDDING_PROVIDER", "local")
    model = model or os.environ.get("WYRD_EMBEDDING_MODEL")

    if provider == "local":
        model = model or "all-MiniLM-L6-v2"
        return SentenceTransformerEmbedder(model)

    elif provider == "openai":
        raise NotImplementedError("OpenAI embeddings not yet implemented")

    elif provider == "voyage":
        raise NotImplementedError("Voyage embeddings not yet implemented")

    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
