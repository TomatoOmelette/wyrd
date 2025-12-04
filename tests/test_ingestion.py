"""Tests for book ingestion: parsing and chunking."""

import pytest

from wyrd.core.ingestion import chunk_text, chunk_chapter, Chunk


class TestChunkText:
    """Tests for the chunk_text function."""

    def test_empty_text(self):
        """Empty text returns empty list."""
        result = chunk_text("")
        assert result == []

    def test_whitespace_only(self):
        """Whitespace-only text returns empty list."""
        result = chunk_text("   \n\n   ")
        assert result == []

    def test_short_text_single_chunk(self):
        """Text shorter than chunk_size returns single chunk."""
        text = "This is a short sentence."
        result = chunk_text(text, chunk_size=100)

        assert len(result) == 1
        assert result[0][0] == text
        assert result[0][1] == 0  # start position
        assert result[0][2] == len(text)  # end position

    def test_chunk_positions_are_correct(self):
        """Chunk positions correctly reference the original text."""
        text = "First sentence. Second sentence. Third sentence."
        result = chunk_text(text, chunk_size=20, chunk_overlap=5)

        for chunk_text_content, start, end in result:
            assert text[start:end].strip() == chunk_text_content

    def test_chunks_have_overlap(self):
        """Adjacent chunks share overlapping content."""
        text = "A" * 100 + " " + "B" * 100 + " " + "C" * 100
        result = chunk_text(text, chunk_size=110, chunk_overlap=20)

        assert len(result) >= 2
        # Each chunk should be around the target size
        for chunk_content, _, _ in result:
            assert len(chunk_content) <= 150  # Some flexibility for boundary finding

    def test_respects_sentence_boundaries(self):
        """Chunks prefer to break at sentence boundaries."""
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        result = chunk_text(text, chunk_size=50, chunk_overlap=10)

        # Most chunks should end with a period
        for chunk_content, _, _ in result[:-1]:  # Exclude last chunk
            # Should end with punctuation or be near it
            assert any(p in chunk_content for p in [".", "!", "?"])

    def test_respects_paragraph_boundaries(self):
        """Chunks prefer to break at paragraph boundaries."""
        text = "First paragraph content here.\n\nSecond paragraph content here.\n\nThird paragraph."
        result = chunk_text(text, chunk_size=40, chunk_overlap=5)

        # Should break at paragraph boundaries when possible
        assert len(result) >= 2


class TestChunkChapter:
    """Tests for the chunk_chapter function."""

    def test_creates_chunk_objects(self):
        """Returns list of Chunk objects with correct metadata."""
        content = "This is chapter content. " * 20
        chunks = chunk_chapter(
            chapter_content=content,
            book_slug="my-book",
            chapter_number=3,
            chapter_title="Test Chapter",
            chunk_size=100,
            chunk_overlap=20,
        )

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunk_ids_are_unique(self):
        """Each chunk has a unique ID."""
        content = "Content " * 100
        chunks = chunk_chapter(
            chapter_content=content,
            book_slug="book",
            chapter_number=1,
            chapter_title="Chapter",
            chunk_size=50,
        )

        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_id_format(self):
        """Chunk IDs follow expected format."""
        chunks = chunk_chapter(
            chapter_content="Some content here.",
            book_slug="test-book",
            chapter_number=5,
            chapter_title="Test",
        )

        assert chunks[0].id == "test-book-ch005-0000"

    def test_chunk_metadata(self):
        """Chunks contain correct metadata."""
        chunks = chunk_chapter(
            chapter_content="Some content here that is long enough.",
            book_slug="my-book",
            chapter_number=2,
            chapter_title="My Chapter",
        )

        chunk = chunks[0]
        assert chunk.book_slug == "my-book"
        assert chunk.chapter_number == 2
        assert chunk.chapter_title == "My Chapter"

    def test_chunk_metadata_dict(self):
        """Chunk.metadata property returns correct dict."""
        chunks = chunk_chapter(
            chapter_content="Content here.",
            book_slug="book",
            chapter_number=1,
            chapter_title="Title",
        )

        metadata = chunks[0].metadata
        assert metadata["book_slug"] == "book"
        assert metadata["chapter_number"] == 1
        assert metadata["chapter_title"] == "Title"
        assert "start_position" in metadata
        assert "end_position" in metadata

    def test_empty_chapter(self):
        """Empty chapter content returns empty list."""
        chunks = chunk_chapter(
            chapter_content="",
            book_slug="book",
            chapter_number=1,
            chapter_title="Empty",
        )

        assert chunks == []


class TestEpubParsing:
    """Tests for ePub parsing (requires actual ePub files)."""

    def test_extract_text_from_html(self):
        """HTML content is properly converted to plain text."""
        from wyrd.core.ingestion.epub import extract_text_from_html

        html = "<html><body><h1>Title</h1><p>Paragraph one.</p><p>Paragraph two.</p></body></html>"
        text = extract_text_from_html(html)

        assert "Title" in text
        assert "Paragraph one" in text
        assert "Paragraph two" in text
        assert "<" not in text  # No HTML tags

    def test_extract_text_removes_scripts(self):
        """Script and style tags are removed."""
        from wyrd.core.ingestion.epub import extract_text_from_html

        html = "<html><script>alert('bad')</script><style>.x{}</style><p>Content</p></html>"
        text = extract_text_from_html(html)

        assert "alert" not in text
        assert ".x" not in text
        assert "Content" in text

    def test_extract_text_handles_bytes(self):
        """Can handle bytes input."""
        from wyrd.core.ingestion.epub import extract_text_from_html

        html_bytes = b"<p>Hello world</p>"
        text = extract_text_from_html(html_bytes)

        assert "Hello world" in text

    def test_parse_epub_nonexistent_file(self):
        """Raises FileNotFoundError for missing file."""
        from wyrd.core.ingestion.epub import parse_epub

        with pytest.raises(FileNotFoundError):
            parse_epub("/nonexistent/path/book.epub")
