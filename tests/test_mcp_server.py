"""Tests for MCP server tools."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from wyrd.mcp_server.server import (
    list_tools,
    call_tool,
    format_results,
)
from wyrd.core.retrieval import SearchResult


class TestFormatResults:
    """Tests for result formatting."""

    def test_format_empty_results(self):
        """Empty results return appropriate message."""
        result = format_results([])
        assert result == "No results found."

    def test_format_citations_only(self):
        """Citations mode shows just references."""
        results = [
            SearchResult(
                chunk_id="id1",
                content="Long content that should not appear in citations mode.",
                book_slug="book",
                book_title="My Book",
                book_author="Author",
                chapter_number=1,
                chapter_title="Chapter One",
                start_position=0,
                end_position=50,
                score=0.9,
            ),
        ]

        formatted = format_results(results, detail="citations")

        assert "My Book" in formatted
        assert "Chapter One" in formatted
        assert "Long content" not in formatted

    def test_format_summaries(self):
        """Summaries mode shows brief excerpts."""
        results = [
            SearchResult(
                chunk_id="id1",
                content="A" * 500,  # Long content
                book_slug="book",
                book_title="Book Title",
                book_author="Author",
                chapter_number=2,
                chapter_title="Chapter Two",
                start_position=0,
                end_position=500,
                score=0.85,
            ),
        ]

        formatted = format_results(results, detail="summaries")

        assert "Book Title" in formatted
        assert "..." in formatted  # Truncated
        assert len(formatted) < 600  # Not full content

    def test_format_full(self):
        """Full mode shows complete content."""
        content = "This is the full content of the chunk."
        results = [
            SearchResult(
                chunk_id="id1",
                content=content,
                book_slug="book",
                book_title="Book",
                book_author="Author",
                chapter_number=1,
                chapter_title="Ch",
                start_position=0,
                end_position=len(content),
                score=0.95,
            ),
        ]

        formatted = format_results(results, detail="full")

        assert content in formatted
        assert "0.95" in formatted  # Score shown
        assert "Book" in formatted

    def test_format_multiple_results(self):
        """Multiple results are numbered."""
        results = [
            SearchResult(
                chunk_id=f"id{i}",
                content=f"Content {i}",
                book_slug="book",
                book_title="Book",
                book_author="Author",
                chapter_number=i,
                chapter_title=f"Chapter {i}",
                start_position=0,
                end_position=10,
                score=0.9 - i * 0.1,
            )
            for i in range(3)
        ]

        formatted = format_results(results, detail="summaries")

        assert "1." in formatted
        assert "2." in formatted
        assert "3." in formatted


class TestListTools:
    """Tests for tool listing."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_tools(self):
        """list_tools returns available tools."""
        tools = await list_tools()

        assert len(tools) >= 2

        tool_names = {t.name for t in tools}
        assert "search_knowledge" in tool_names
        assert "explore_library" in tool_names

    @pytest.mark.asyncio
    async def test_search_knowledge_tool_schema(self):
        """search_knowledge tool has correct schema."""
        tools = await list_tools()
        search_tool = next(t for t in tools if t.name == "search_knowledge")

        schema = search_tool.inputSchema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "query" in schema["required"]
        assert "limit" in schema["properties"]
        assert "sources" in schema["properties"]
        assert "detail" in schema["properties"]

    @pytest.mark.asyncio
    async def test_explore_library_tool_schema(self):
        """explore_library tool has correct schema."""
        tools = await list_tools()
        explore_tool = next(t for t in tools if t.name == "explore_library")

        schema = explore_tool.inputSchema
        assert schema["type"] == "object"
        assert "detail" in schema["properties"]


class TestCallTool:
    """Tests for tool execution."""

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """Unknown tool returns error."""
        result = await call_tool("nonexistent_tool", {})

        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_search_knowledge_requires_query(self):
        """search_knowledge without query returns error."""
        result = await call_tool("search_knowledge", {})

        assert len(result) == 1
        assert "Error" in result[0].text or "query" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_search_knowledge_with_mock(self, temp_dir, mock_embeddings):
        """search_knowledge returns formatted results."""
        from wyrd.core.indexing import MetadataStore, VectorStore
        from wyrd.core.ingestion import Chunk
        from wyrd.core.retrieval import SemanticSearch

        # Set up stores
        vector_store = VectorStore(storage_path=temp_dir / "vectors")
        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")

        metadata_store.add_book(slug="book", title="Test Book", author="Author")

        chunks = [
            Chunk(id="book-ch001-0000", content="Test content here.", book_slug="book",
                  chapter_number=1, chapter_title="Ch", start_position=0, end_position=20),
        ]
        embeddings = [mock_embeddings() for _ in chunks]
        vector_store.add_chunks(chunks, embeddings)

        # Mock the embedder
        mock_embedder = MagicMock()
        mock_embedder.embed.return_value = [mock_embeddings()]

        search_engine = SemanticSearch(
            vector_store=vector_store,
            metadata_store=metadata_store,
            embedder=mock_embedder,
        )

        # Patch the get_search_engine function
        with patch("wyrd.mcp_server.server.get_search_engine", return_value=search_engine):
            result = await call_tool("search_knowledge", {"query": "test"})

        assert len(result) == 1
        assert "Test Book" in result[0].text

    @pytest.mark.asyncio
    async def test_explore_library_empty(self, temp_dir):
        """explore_library on empty library shows message."""
        from wyrd.core.indexing import MetadataStore

        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")

        with patch("wyrd.mcp_server.server.get_metadata_store", return_value=metadata_store):
            result = await call_tool("explore_library", {})

        assert len(result) == 1
        assert "empty" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_explore_library_with_books(self, temp_dir):
        """explore_library lists subjects overview."""
        from wyrd.core.indexing import MetadataStore

        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")
        metadata_store.add_book(slug="book1", title="First Book", author="Author One", subject="parenting")
        metadata_store.add_book(slug="book2", title="Second Book", author="Author Two", subject="parenting")

        with patch("wyrd.mcp_server.server.get_metadata_store", return_value=metadata_store):
            # Without subject, shows subjects overview
            result = await call_tool("explore_library", {})

        assert len(result) == 1
        assert "parenting" in result[0].text
        assert "2 book" in result[0].text

    @pytest.mark.asyncio
    async def test_explore_library_with_subject_filter(self, temp_dir):
        """explore_library lists books in a subject."""
        from wyrd.core.indexing import MetadataStore

        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")
        metadata_store.add_book(slug="book1", title="First Book", author="Author One", subject="parenting")
        metadata_store.add_book(slug="book2", title="Second Book", author="Author Two", subject="networking")

        with patch("wyrd.mcp_server.server.get_metadata_store", return_value=metadata_store):
            result = await call_tool("explore_library", {"subject": "parenting", "detail": "summaries"})

        assert len(result) == 1
        assert "First Book" in result[0].text
        assert "Second Book" not in result[0].text

    @pytest.mark.asyncio
    async def test_explore_library_detail_levels(self, temp_dir):
        """explore_library respects detail level."""
        from wyrd.core.indexing import MetadataStore

        metadata_store = MetadataStore(storage_path=temp_dir / "metadata.db")
        metadata_store.add_book(slug="mybook", title="My Book", author="My Author", subject="general")
        metadata_store.update_chunk_count("mybook", 100)

        with patch("wyrd.mcp_server.server.get_metadata_store", return_value=metadata_store):
            # Names only (with subject filter to see books)
            result_names = await call_tool("explore_library", {"subject": "general", "detail": "names"})
            assert "My Book" in result_names[0].text
            assert "My Author" not in result_names[0].text

            # Full details
            result_full = await call_tool("explore_library", {"subject": "general", "detail": "full"})
            assert "My Book" in result_full[0].text
            assert "My Author" in result_full[0].text
            assert "100" in result_full[0].text  # chunk count
