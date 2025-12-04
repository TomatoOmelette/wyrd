"""Tests for indexing: vector storage and metadata storage."""

import pytest
from datetime import datetime

from wyrd.core.indexing import MetadataStore, VectorStore, BookRecord
from wyrd.core.ingestion import Chunk


class TestVectorStore:
    """Tests for ChromaDB vector storage."""

    def test_add_and_count_chunks(self, vector_store, sample_chunks, mock_embeddings):
        """Can add chunks and count them."""
        embeddings = [mock_embeddings() for _ in sample_chunks]

        vector_store.add_chunks(sample_chunks, embeddings)

        assert vector_store.count() == 3

    def test_add_empty_chunks(self, vector_store):
        """Adding empty list does nothing."""
        vector_store.add_chunks([], [])
        assert vector_store.count() == 0

    def test_add_mismatched_lengths_raises(self, vector_store, sample_chunks, mock_embeddings):
        """Raises error if chunks and embeddings have different lengths."""
        embeddings = [mock_embeddings()]  # Only one embedding

        with pytest.raises(ValueError, match="Mismatch"):
            vector_store.add_chunks(sample_chunks, embeddings)

    def test_search_returns_results(self, vector_store, sample_chunks, mock_embeddings):
        """Search returns matching chunks."""
        embeddings = [mock_embeddings() for _ in sample_chunks]
        vector_store.add_chunks(sample_chunks, embeddings)

        query_embedding = mock_embeddings()
        results = vector_store.search(query_embedding, n_results=2)

        assert len(results) == 2
        assert all("id" in r for r in results)
        assert all("content" in r for r in results)
        assert all("metadata" in r for r in results)
        assert all("distance" in r for r in results)

    def test_search_with_book_filter(self, vector_store, mock_embeddings):
        """Search can filter by book slug."""
        chunks = [
            Chunk(
                id="book1-ch001-0000",
                content="Content from book one.",
                book_slug="book1",
                chapter_number=1,
                chapter_title="Chapter",
                start_position=0,
                end_position=25,
            ),
            Chunk(
                id="book2-ch001-0000",
                content="Content from book two.",
                book_slug="book2",
                chapter_number=1,
                chapter_title="Chapter",
                start_position=0,
                end_position=25,
            ),
        ]
        embeddings = [mock_embeddings() for _ in chunks]
        vector_store.add_chunks(chunks, embeddings)

        # Search only in book1
        results = vector_store.search(
            mock_embeddings(),
            n_results=10,
            where={"book_slug": "book1"},
        )

        assert len(results) == 1
        assert results[0]["metadata"]["book_slug"] == "book1"

    def test_delete_by_book(self, vector_store, mock_embeddings):
        """Can delete all chunks for a book."""
        chunks = [
            Chunk(
                id="book1-ch001-0000",
                content="Book one content.",
                book_slug="book1",
                chapter_number=1,
                chapter_title="Ch",
                start_position=0,
                end_position=20,
            ),
            Chunk(
                id="book1-ch001-0001",
                content="More book one content.",
                book_slug="book1",
                chapter_number=1,
                chapter_title="Ch",
                start_position=21,
                end_position=45,
            ),
            Chunk(
                id="book2-ch001-0000",
                content="Book two content.",
                book_slug="book2",
                chapter_number=1,
                chapter_title="Ch",
                start_position=0,
                end_position=20,
            ),
        ]
        embeddings = [mock_embeddings() for _ in chunks]
        vector_store.add_chunks(chunks, embeddings)

        assert vector_store.count() == 3

        deleted = vector_store.delete_by_book("book1")

        assert deleted == 2
        assert vector_store.count() == 1
        assert vector_store.count(book_slug="book2") == 1

    def test_get_book_slugs(self, vector_store, mock_embeddings):
        """Can get unique book slugs."""
        chunks = [
            Chunk(id="a-1", content="A", book_slug="alpha", chapter_number=1, chapter_title="", start_position=0, end_position=1),
            Chunk(id="a-2", content="A", book_slug="alpha", chapter_number=1, chapter_title="", start_position=0, end_position=1),
            Chunk(id="b-1", content="B", book_slug="beta", chapter_number=1, chapter_title="", start_position=0, end_position=1),
        ]
        embeddings = [mock_embeddings() for _ in chunks]
        vector_store.add_chunks(chunks, embeddings)

        slugs = vector_store.get_book_slugs()

        assert sorted(slugs) == ["alpha", "beta"]

    def test_count_by_book(self, vector_store, sample_chunks, mock_embeddings):
        """Can count chunks filtered by book."""
        embeddings = [mock_embeddings() for _ in sample_chunks]
        vector_store.add_chunks(sample_chunks, embeddings)

        count = vector_store.count(book_slug="test-book")
        assert count == 3

        count = vector_store.count(book_slug="nonexistent")
        assert count == 0


class TestMetadataStore:
    """Tests for SQLite metadata storage."""

    def test_add_and_get_book(self, metadata_store):
        """Can add and retrieve a book."""
        book = metadata_store.add_book(
            slug="test-book",
            title="Test Book",
            author="Test Author",
            file_path="/path/to/book.epub",
        )

        assert book.slug == "test-book"
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.file_path == "/path/to/book.epub"
        assert isinstance(book.added_at, datetime)

        # Retrieve it
        retrieved = metadata_store.get_book("test-book")
        assert retrieved is not None
        assert retrieved.title == "Test Book"

    def test_get_nonexistent_book(self, metadata_store):
        """Returns None for nonexistent book."""
        book = metadata_store.get_book("nonexistent")
        assert book is None

    def test_book_exists(self, metadata_store):
        """Can check if book exists."""
        assert not metadata_store.book_exists("test-book")

        metadata_store.add_book(slug="test-book", title="Test", author="Author")

        assert metadata_store.book_exists("test-book")

    def test_add_book_upserts(self, metadata_store):
        """Adding book with same slug updates it."""
        metadata_store.add_book(slug="book", title="Original", author="Author1")
        metadata_store.add_book(slug="book", title="Updated", author="Author2")

        book = metadata_store.get_book("book")
        assert book.title == "Updated"
        assert book.author == "Author2"

    def test_get_all_books(self, metadata_store):
        """Can get all books."""
        metadata_store.add_book(slug="book1", title="Book One", author="Author")
        metadata_store.add_book(slug="book2", title="Book Two", author="Author")

        books = metadata_store.get_all_books()

        assert len(books) == 2
        titles = {b.title for b in books}
        assert titles == {"Book One", "Book Two"}

    def test_get_all_books_empty(self, metadata_store):
        """Returns empty list when no books."""
        books = metadata_store.get_all_books()
        assert books == []

    def test_delete_book(self, metadata_store):
        """Can delete a book."""
        metadata_store.add_book(slug="book", title="Book", author="Author")
        assert metadata_store.book_exists("book")

        deleted = metadata_store.delete_book("book")

        assert deleted is True
        assert not metadata_store.book_exists("book")

    def test_delete_nonexistent_book(self, metadata_store):
        """Deleting nonexistent book returns False."""
        deleted = metadata_store.delete_book("nonexistent")
        assert deleted is False

    def test_add_and_get_chapters(self, metadata_store):
        """Can add and retrieve chapters."""
        metadata_store.add_book(slug="book", title="Book", author="Author")
        metadata_store.add_chapters(
            "book",
            [
                (1, "Introduction", 0, 1000),
                (2, "Chapter One", 1001, 5000),
                (3, "Conclusion", 5001, 6000),
            ],
        )

        chapters = metadata_store.get_chapters("book")

        assert len(chapters) == 3
        assert chapters[0].number == 1
        assert chapters[0].title == "Introduction"
        assert chapters[1].number == 2
        assert chapters[2].number == 3

    def test_add_chapters_replaces_existing(self, metadata_store):
        """Adding chapters replaces existing ones."""
        metadata_store.add_book(slug="book", title="Book", author="Author")
        metadata_store.add_chapters("book", [(1, "Old", 0, 100)])
        metadata_store.add_chapters("book", [(1, "New", 0, 200), (2, "Extra", 201, 300)])

        chapters = metadata_store.get_chapters("book")

        assert len(chapters) == 2
        assert chapters[0].title == "New"

    def test_update_chunk_count(self, metadata_store):
        """Can update chunk count."""
        metadata_store.add_book(slug="book", title="Book", author="Author")

        book = metadata_store.get_book("book")
        assert book.chunk_count == 0

        metadata_store.update_chunk_count("book", 150)

        book = metadata_store.get_book("book")
        assert book.chunk_count == 150

    def test_delete_book_cascades_to_chapters(self, metadata_store):
        """Deleting book also deletes chapters."""
        metadata_store.add_book(slug="book", title="Book", author="Author")
        metadata_store.add_chapters("book", [(1, "Ch1", 0, 100)])

        metadata_store.delete_book("book")

        chapters = metadata_store.get_chapters("book")
        assert chapters == []
