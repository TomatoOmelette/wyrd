"""Vector storage using ChromaDB."""

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from wyrd.core.ingestion import Chunk


class VectorStore:
    """ChromaDB-based vector storage."""

    def __init__(
        self,
        storage_path: str | Path | None = None,
        collection_name: str = "book_chunks",
    ):
        """
        Initialize the vector store.

        Args:
            storage_path: Path to persist the database. Defaults to WYRD_STORAGE_PATH/vectors
            collection_name: Name of the collection to use
        """
        if storage_path is None:
            base_path = os.environ.get("WYRD_STORAGE_PATH", "./storage")
            storage_path = Path(base_path) / "vectors"
        else:
            storage_path = Path(storage_path)

        storage_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(storage_path),
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """
        Add chunks with their embeddings to the store.

        Args:
            chunks: List of Chunk objects
            embeddings: List of embedding vectors (same order as chunks)
        """
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings"
            )

        self.collection.add(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=[c.content for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> list[dict]:
        """
        Search for similar chunks.

        Args:
            query_embedding: The query vector
            n_results: Number of results to return
            where: Optional filter conditions (e.g., {"book_slug": "my-book"})

        Returns:
            List of result dicts with id, content, metadata, and distance
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Flatten the results (query returns nested lists)
        output = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                output.append(
                    {
                        "id": chunk_id,
                        "content": results["documents"][0][i] if results["documents"] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else None,
                    }
                )

        return output

    def delete_by_book(self, book_slug: str) -> int:
        """
        Delete all chunks for a book.

        Args:
            book_slug: The book identifier

        Returns:
            Number of chunks deleted
        """
        # Get all IDs for this book
        results = self.collection.get(
            where={"book_slug": book_slug},
            include=[],
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            return len(results["ids"])

        return 0

    def get_book_slugs(self) -> list[str]:
        """Get all unique book slugs in the store."""
        # ChromaDB doesn't have a direct way to get unique values
        # So we get all metadata and extract unique slugs
        results = self.collection.get(include=["metadatas"])

        slugs = set()
        if results["metadatas"]:
            for metadata in results["metadatas"]:
                if metadata and "book_slug" in metadata:
                    slugs.add(metadata["book_slug"])

        return sorted(slugs)

    def count(self, book_slug: str | None = None) -> int:
        """
        Count chunks in the store.

        Args:
            book_slug: Optional filter by book

        Returns:
            Number of chunks
        """
        if book_slug:
            results = self.collection.get(
                where={"book_slug": book_slug},
                include=[],
            )
            return len(results["ids"]) if results["ids"] else 0
        else:
            return self.collection.count()

    def get_chunks_by_chapter(
        self,
        book_slug: str,
        chapter_number: int,
    ) -> list[dict]:
        """
        Get all chunks for a specific chapter.

        Args:
            book_slug: The book identifier
            chapter_number: The chapter number

        Returns:
            List of chunk dicts with id, content, and metadata
        """
        results = self.collection.get(
            where={
                "$and": [
                    {"book_slug": {"$eq": book_slug}},
                    {"chapter_number": {"$eq": chapter_number}},
                ]
            },
            include=["documents", "metadatas"],
        )

        output = []
        if results["ids"]:
            for i, chunk_id in enumerate(results["ids"]):
                output.append(
                    {
                        "id": chunk_id,
                        "content": results["documents"][i] if results["documents"] else None,
                        "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    }
                )

        # Sort by position within chapter
        output.sort(key=lambda x: x["metadata"].get("position", 0))
        return output
