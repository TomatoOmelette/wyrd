"""Semantic search over the knowledge base."""

from dataclasses import dataclass
from typing import Any

from wyrd.core.indexing import MetadataStore, VectorStore
from wyrd.core.ingestion import Embedder, get_embedder


@dataclass
class SearchResult:
    """A search result with content and metadata."""

    chunk_id: str
    content: str
    book_slug: str
    book_title: str
    book_author: str
    chapter_number: int
    chapter_title: str
    start_position: int
    end_position: int
    score: float  # Similarity score (higher is better)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "book_slug": self.book_slug,
            "book_title": self.book_title,
            "book_author": self.book_author,
            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "score": self.score,
        }

    @property
    def citation(self) -> str:
        """Format as a citation string."""
        return f"[{self.book_title}, Ch. {self.chapter_number}: \"{self.chapter_title}\"]"


class SemanticSearch:
    """Semantic search engine."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        metadata_store: MetadataStore | None = None,
        embedder: Embedder | None = None,
    ):
        """
        Initialize the search engine.

        Args:
            vector_store: Optional VectorStore instance
            metadata_store: Optional MetadataStore instance
            embedder: Optional Embedder instance
        """
        self.vector_store = vector_store or VectorStore()
        self.metadata_store = metadata_store or MetadataStore()
        self._embedder = embedder

    @property
    def embedder(self) -> Embedder:
        """Lazy-load the embedder."""
        if self._embedder is None:
            self._embedder = get_embedder()
        return self._embedder

    def search(
        self,
        query: str,
        n_results: int = 10,
        book_slugs: list[str] | None = None,
        subject: str | None = None,
    ) -> list[SearchResult]:
        """
        Search for chunks matching the query.

        Args:
            query: The search query
            n_results: Maximum number of results to return
            book_slugs: Optional list of book slugs to filter by
            subject: Optional subject to filter by (gets all books in that subject)

        Returns:
            List of SearchResult objects, ordered by relevance
        """
        # If subject is specified, get all books in that subject
        if subject:
            subject_books = self.metadata_store.get_books_by_subject(subject)
            subject_slugs = [b.slug for b in subject_books]
            if book_slugs:
                # Intersect with any explicit book_slugs filter
                book_slugs = [s for s in book_slugs if s in subject_slugs]
            else:
                book_slugs = subject_slugs

            if not book_slugs:
                # No books match the filters
                return []

        # Embed the query
        query_embedding = self.embedder.embed([query])[0]

        # Build filter
        where = None
        if book_slugs:
            if len(book_slugs) == 1:
                where = {"book_slug": book_slugs[0]}
            else:
                where = {"book_slug": {"$in": book_slugs}}

        # Search vectors
        raw_results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        # Enrich with book metadata
        results = []
        book_cache: dict[str, tuple[str, str]] = {}  # slug -> (title, author)

        for raw in raw_results:
            metadata = raw["metadata"]
            book_slug = metadata.get("book_slug", "")

            # Get book info (cached)
            if book_slug not in book_cache:
                book = self.metadata_store.get_book(book_slug)
                if book:
                    book_cache[book_slug] = (book.title, book.author)
                else:
                    book_cache[book_slug] = (book_slug, "Unknown")

            book_title, book_author = book_cache[book_slug]

            # Convert distance to similarity score (cosine distance -> similarity)
            # ChromaDB returns distance, so smaller is better
            # Convert to score where higher is better
            distance = raw.get("distance", 0)
            score = 1 - distance if distance is not None else 0

            results.append(
                SearchResult(
                    chunk_id=raw["id"],
                    content=raw["content"] or "",
                    book_slug=book_slug,
                    book_title=book_title,
                    book_author=book_author,
                    chapter_number=metadata.get("chapter_number", 0),
                    chapter_title=metadata.get("chapter_title", ""),
                    start_position=metadata.get("start_position", 0),
                    end_position=metadata.get("end_position", 0),
                    score=score,
                )
            )

        return results


# Module-level convenience function
_search_engine: SemanticSearch | None = None


def get_search_engine() -> SemanticSearch:
    """Get or create the default search engine."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SemanticSearch()
    return _search_engine


def search(
    query: str,
    n_results: int = 10,
    book_slugs: list[str] | None = None,
    subject: str | None = None,
) -> list[SearchResult]:
    """
    Convenience function for searching.

    Args:
        query: The search query
        n_results: Maximum number of results
        book_slugs: Optional filter by book slugs
        subject: Optional filter by subject

    Returns:
        List of SearchResult objects
    """
    return get_search_engine().search(query, n_results, book_slugs, subject)
