"""Tests for CLI commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from wyrd.cli import app


runner = CliRunner()


class TestVersionCommand:
    """Tests for version flag."""

    def test_version_flag(self):
        """--version shows version."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "wyrd version" in result.output
        assert "0.1.0" in result.output


class TestListCommand:
    """Tests for list command."""

    def test_list_empty(self, temp_dir):
        """List shows message when no books."""
        with patch("wyrd.core.indexing.MetadataStore") as MockStore:
            mock_store = MagicMock()
            mock_store.get_all_books.return_value = []
            MockStore.return_value = mock_store

            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No books" in result.output

    def test_list_with_books(self, temp_dir):
        """List shows books in table."""
        from datetime import datetime
        from wyrd.core.indexing import BookRecord

        mock_books = [
            BookRecord(
                slug="book1",
                title="First Book",
                author="Author One",
                subject="parenting",
                file_path="/path/to/book1.epub",
                added_at=datetime(2024, 1, 15),
                chunk_count=100,
            ),
            BookRecord(
                slug="book2",
                title="Second Book",
                author="Author Two",
                subject="parenting",
                file_path="/path/to/book2.epub",
                added_at=datetime(2024, 2, 20),
                chunk_count=200,
            ),
        ]

        with patch("wyrd.core.indexing.MetadataStore") as MockStore:
            mock_store = MagicMock()
            mock_store.get_all_books.return_value = mock_books
            MockStore.return_value = mock_store

            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "First Book" in result.output
        assert "Second Book" in result.output
        assert "Author One" in result.output
        assert "book1" in result.output


class TestRemoveCommand:
    """Tests for remove command."""

    def test_remove_nonexistent(self):
        """Remove shows error for nonexistent book."""
        with patch("wyrd.core.indexing.MetadataStore") as MockStore:
            mock_store = MagicMock()
            mock_store.get_book.return_value = None
            MockStore.return_value = mock_store

            result = runner.invoke(app, ["remove", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_remove_with_confirmation(self):
        """Remove prompts for confirmation."""
        from datetime import datetime
        from wyrd.core.indexing import BookRecord

        mock_book = BookRecord(
            slug="test",
            title="Test Book",
            author="Author",
            subject="general",
            file_path=None,
            added_at=datetime.now(),
            chunk_count=50,
        )

        with patch("wyrd.core.indexing.MetadataStore") as MockMeta, \
             patch("wyrd.core.indexing.VectorStore") as MockVector:

            mock_meta = MagicMock()
            mock_meta.get_book.return_value = mock_book
            MockMeta.return_value = mock_meta

            mock_vector = MagicMock()
            mock_vector.delete_by_book.return_value = 50
            MockVector.return_value = mock_vector

            # Decline confirmation
            result = runner.invoke(app, ["remove", "test"], input="n\n")

        assert "Cancelled" in result.output

    def test_remove_with_force(self):
        """Remove --force skips confirmation."""
        from datetime import datetime
        from wyrd.core.indexing import BookRecord

        mock_book = BookRecord(
            slug="test",
            title="Test Book",
            author="Author",
            subject="general",
            file_path=None,
            added_at=datetime.now(),
            chunk_count=50,
        )

        with patch("wyrd.core.indexing.MetadataStore") as MockMeta, \
             patch("wyrd.core.indexing.VectorStore") as MockVector:

            mock_meta = MagicMock()
            mock_meta.get_book.return_value = mock_book
            MockMeta.return_value = mock_meta

            mock_vector = MagicMock()
            mock_vector.delete_by_book.return_value = 50
            MockVector.return_value = mock_vector

            result = runner.invoke(app, ["remove", "test", "--force"])

        assert result.exit_code == 0
        assert "Removed" in result.output
        mock_meta.delete_book.assert_called_once_with("test")


class TestSearchCommand:
    """Tests for search command."""

    def test_search_no_results(self):
        """Search shows message when no results."""
        with patch("wyrd.core.retrieval.search") as mock_search:
            mock_search.return_value = []

            result = runner.invoke(app, ["search", "nonexistent query"])

        assert result.exit_code == 0
        assert "No results" in result.output

    def test_search_with_results(self):
        """Search shows formatted results."""
        from wyrd.core.retrieval import SearchResult

        mock_results = [
            SearchResult(
                chunk_id="book-ch001-0000",
                content="This is the matching content from the book.",
                book_slug="book",
                book_title="Parenting Book",
                book_author="Author",
                chapter_number=1,
                chapter_title="Introduction",
                start_position=0,
                end_position=45,
                score=0.85,
            ),
        ]

        with patch("wyrd.core.retrieval.search") as mock_search:
            mock_search.return_value = mock_results

            result = runner.invoke(app, ["search", "parenting"])

        assert result.exit_code == 0
        assert "Parenting Book" in result.output
        assert "matching content" in result.output
        assert "0.85" in result.output

    def test_search_with_limit(self):
        """Search respects --limit option."""
        with patch("wyrd.core.retrieval.search") as mock_search:
            mock_search.return_value = []

            runner.invoke(app, ["search", "query", "--limit", "3"])

            mock_search.assert_called_once_with("query", n_results=3, book_slugs=None, subject=None)

    def test_search_with_source_filter(self):
        """Search respects --source filter."""
        with patch("wyrd.core.retrieval.search") as mock_search:
            mock_search.return_value = []

            runner.invoke(app, ["search", "query", "--source", "my-book"])

            mock_search.assert_called_once_with("query", n_results=5, book_slugs=["my-book"], subject=None)

    def test_search_with_subject_filter(self):
        """Search respects --subject filter."""
        with patch("wyrd.core.retrieval.search") as mock_search:
            mock_search.return_value = []

            runner.invoke(app, ["search", "query", "--subject", "parenting"])

            mock_search.assert_called_once_with("query", n_results=5, book_slugs=None, subject="parenting")


class TestAddCommand:
    """Tests for add command."""

    def test_add_nonexistent_file(self):
        """Add shows error for nonexistent file."""
        result = runner.invoke(app, ["add", "/nonexistent/book.epub"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_add_unsupported_format(self, temp_dir):
        """Add shows error for unsupported formats."""
        # Create a dummy file
        dummy_file = temp_dir / "book.pdf"
        dummy_file.write_text("dummy")

        result = runner.invoke(app, ["add", str(dummy_file)])

        assert result.exit_code == 1
        assert "Unsupported" in result.output


class TestServeCommand:
    """Tests for serve command."""

    def test_serve_unsupported_transport(self):
        """Serve shows error for unsupported transport."""
        result = runner.invoke(app, ["serve", "--transport", "http"])

        assert result.exit_code == 1
        assert "not yet supported" in result.output


class TestBuildCommand:
    """Tests for build command."""

    def test_build_shows_message(self):
        """Build shows informational message."""
        result = runner.invoke(app, ["build"])

        assert result.exit_code == 0
        assert "automatically" in result.output.lower()


class TestTopicsCommand:
    """Tests for topics command."""

    def test_topics_empty_message(self):
        """Topics shows empty message when no topics."""
        with patch("wyrd.core.topics.TopicRegistry") as MockRegistry:
            mock_registry = MagicMock()
            mock_registry.get_all_topics.return_value = []
            MockRegistry.return_value = mock_registry

            result = runner.invoke(app, ["topics"])

        assert result.exit_code == 0
        assert "No topics found" in result.output


class TestConceptsCommand:
    """Tests for concepts command."""

    def test_concepts_empty_message(self):
        """Concepts shows empty message when no concepts."""
        result = runner.invoke(app, ["concepts"])

        assert result.exit_code == 0
        assert "No concepts" in result.output
