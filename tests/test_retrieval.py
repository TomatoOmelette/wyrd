"""Tests for retrieval: semantic search."""

import pytest
from unittest.mock import MagicMock, patch

from wyrd.core.retrieval import SemanticSearch, SearchResult
from wyrd.core.indexing import MetadataStore, VectorStore
from wyrd.core.ingestion import Chunk


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_to_dict(self):
        """SearchResult can be converted to dict."""
        result = SearchResult(
            chunk_id="book-ch001-0000",
            content="Some content here.",
            book_slug="book",
            book_title="My Book",
            book_author="Author Name",
            chapter_number=1,
            chapter_title="Introduction",
            start_position=0,
            end_position=20,
            score=0.85,
        )

        d = result.to_dict()

        assert d["chunk_id"] == "book-ch001-0000"
        assert d["content"] == "Some content here."
        assert d["book_slug"] == "book"
        assert d["book_title"] == "My Book"
        assert d["score"] == 0.85

    def test_citation_format(self):
        """SearchResult produces correct citation format."""
        result = SearchResult(
            chunk_id="id",
            content="Content",
            book_slug="slug",
            book_title="Good Inside",
            book_author="Dr. Becky Kennedy",
            chapter_number=3,
            chapter_title="Connection Capital",
            start_position=0,
            end_position=10,
            score=0.9,
        )

        citation = result.citation

        assert "Good Inside" in citation
        assert "3" in citation
        assert "Connection Capital" in citation


class TestSemanticSearch:
    """Tests for SemanticSearch engine."""

    def test_search_with_mocked_stores(self, temp_dir, mock_embeddings):
        """Search integrates vector store and metadata store."""
        # Create stores
        vector_store = VectorStore(storage_path=temp_dir / "vectors")
        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")

        # Add a book to metadata
        metadata_store.add_book(
            slug="test-book",
            title="Test Parenting Book",
            author="Test Author",
        )

        # Add chunks to vector store
        chunks = [
            Chunk(
                id="test-book-ch001-0000",
                content="Children need connection before correction.",
                book_slug="test-book",
                chapter_number=1,
                chapter_title="Basics",
                start_position=0,
                end_position=45,
            ),
            Chunk(
                id="test-book-ch001-0001",
                content="Emotion coaching helps children regulate.",
                book_slug="test-book",
                chapter_number=1,
                chapter_title="Basics",
                start_position=46,
                end_position=90,
            ),
        ]
        embeddings = [mock_embeddings() for _ in chunks]
        vector_store.add_chunks(chunks, embeddings)

        # Create search engine with mocked embedder
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [mock_embeddings()]

        search_engine = SemanticSearch(
            vector_store=vector_store,
            metadata_store=metadata_store,
            embedder=mock_embedder,
        )

        # Search
        results = search_engine.search("how to connect with kids", n_results=2)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.book_title == "Test Parenting Book" for r in results)
        assert all(r.book_author == "Test Author" for r in results)

    def test_search_with_book_filter(self, temp_dir, mock_embeddings):
        """Search can filter by book slugs."""
        vector_store = VectorStore(storage_path=temp_dir / "vectors")
        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")

        # Add two books
        metadata_store.add_book(slug="book1", title="Book One", author="Author 1")
        metadata_store.add_book(slug="book2", title="Book Two", author="Author 2")

        # Add chunks from both books
        chunks = [
            Chunk(id="book1-ch001-0000", content="Content from book one.", book_slug="book1",
                  chapter_number=1, chapter_title="Ch", start_position=0, end_position=25),
            Chunk(id="book2-ch001-0000", content="Content from book two.", book_slug="book2",
                  chapter_number=1, chapter_title="Ch", start_position=0, end_position=25),
        ]
        embeddings = [mock_embeddings() for _ in chunks]
        vector_store.add_chunks(chunks, embeddings)

        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [mock_embeddings()]

        search_engine = SemanticSearch(
            vector_store=vector_store,
            metadata_store=metadata_store,
            embedder=mock_embedder,
        )

        # Search only book1
        results = search_engine.search("content", n_results=10, book_slugs=["book1"])

        assert len(results) == 1
        assert results[0].book_slug == "book1"

    def test_search_returns_scores(self, temp_dir, mock_embeddings):
        """Search results include similarity scores."""
        vector_store = VectorStore(storage_path=temp_dir / "vectors")
        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")

        metadata_store.add_book(slug="book", title="Book", author="Author")

        chunks = [
            Chunk(id="book-ch001-0000", content="Some content.", book_slug="book",
                  chapter_number=1, chapter_title="Ch", start_position=0, end_position=15),
        ]
        embeddings = [mock_embeddings() for _ in chunks]
        vector_store.add_chunks(chunks, embeddings)

        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [mock_embeddings()]

        search_engine = SemanticSearch(
            vector_store=vector_store,
            metadata_store=metadata_store,
            embedder=mock_embedder,
        )

        results = search_engine.search("query")

        assert len(results) == 1
        assert isinstance(results[0].score, float)
        assert 0 <= results[0].score <= 1

    def test_search_empty_database(self, temp_dir, mock_embeddings):
        """Search on empty database returns empty list."""
        vector_store = VectorStore(storage_path=temp_dir / "vectors")
        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")

        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [mock_embeddings()]

        search_engine = SemanticSearch(
            vector_store=vector_store,
            metadata_store=metadata_store,
            embedder=mock_embedder,
        )

        results = search_engine.search("anything")

        assert results == []

    def test_search_handles_missing_book_metadata(self, temp_dir, mock_embeddings):
        """Search handles chunks without corresponding book metadata gracefully."""
        vector_store = VectorStore(storage_path=temp_dir / "vectors")
        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")

        # Add chunk but NOT the book metadata
        chunks = [
            Chunk(id="orphan-ch001-0000", content="Orphan content.", book_slug="orphan-book",
                  chapter_number=1, chapter_title="Ch", start_position=0, end_position=15),
        ]
        embeddings = [mock_embeddings() for _ in chunks]
        vector_store.add_chunks(chunks, embeddings)

        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [mock_embeddings()]

        search_engine = SemanticSearch(
            vector_store=vector_store,
            metadata_store=metadata_store,
            embedder=mock_embedder,
        )

        # Should not crash, should use fallback values
        results = search_engine.search("orphan")

        assert len(results) == 1
        assert results[0].book_slug == "orphan-book"
        assert results[0].book_title == "orphan-book"  # Falls back to slug
        assert results[0].book_author == "Unknown"
