"""MCP server for Wyrd."""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from wyrd.core.indexing import MetadataStore
from wyrd.core.retrieval import SemanticSearch, SearchResult


# Create the MCP server
server = Server("wyrd")

# Lazy-loaded instances
_search_engine: SemanticSearch | None = None
_metadata_store: MetadataStore | None = None


def get_search_engine() -> SemanticSearch:
    """Get or create the search engine."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SemanticSearch()
    return _search_engine


def get_metadata_store() -> MetadataStore:
    """Get or create the metadata store."""
    global _metadata_store
    if _metadata_store is None:
        _metadata_store = MetadataStore()
    return _metadata_store


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_knowledge",
            description=(
                "Search the book knowledge base using semantic search. "
                "Returns relevant passages with citations to specific books and chapters. "
                "Use the 'subject' parameter to search within a specific subject area."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query - a question or topic to find information about",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5,
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject/collection to search within (e.g., 'parenting', 'networking')",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of book slugs to search within",
                    },
                    "detail": {
                        "type": "string",
                        "enum": ["citations", "summaries", "full"],
                        "description": (
                            "Level of detail: 'citations' (just references), "
                            "'summaries' (brief excerpts), 'full' (complete passages). Default: summaries"
                        ),
                        "default": "summaries",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="explore_library",
            description=(
                "Explore the knowledge base structure. "
                "List available subjects and books. "
                "Use this to understand what subjects and books are available before searching."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Filter by subject (omit to see all subjects and books)",
                    },
                    "detail": {
                        "type": "string",
                        "enum": ["names", "summaries", "full"],
                        "description": (
                            "Level of detail: 'names' (just titles), "
                            "'summaries' (with authors), 'full' (all metadata). Default: summaries"
                        ),
                        "default": "summaries",
                    },
                },
            },
        ),
    ]


def format_results(
    results: list[SearchResult],
    detail: str = "summaries",
) -> str:
    """Format search results based on detail level."""
    if not results:
        return "No results found."

    output_parts = []

    for i, result in enumerate(results, 1):
        if detail == "citations":
            # Just the citation
            output_parts.append(f"{i}. {result.citation}")

        elif detail == "summaries":
            # Citation with a brief excerpt
            excerpt = result.content[:300]
            if len(result.content) > 300:
                excerpt += "..."
            output_parts.append(
                f"{i}. {result.citation}\n"
                f"   {excerpt}\n"
            )

        else:  # full
            # Complete content with citation
            output_parts.append(
                f"{i}. {result.citation}\n"
                f"   Score: {result.score:.3f}\n"
                f"   ---\n"
                f"   {result.content}\n"
            )

    return "\n".join(output_parts)


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if name == "search_knowledge":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        subject = arguments.get("subject")
        sources = arguments.get("sources")
        detail = arguments.get("detail", "summaries")

        if not query:
            return [TextContent(type="text", text="Error: query is required")]

        try:
            search_engine = get_search_engine()
            results = search_engine.search(
                query=query,
                n_results=limit,
                book_slugs=sources,
                subject=subject,
            )

            formatted = format_results(results, detail)
            return [TextContent(type="text", text=formatted)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error searching: {e}")]

    elif name == "explore_library":
        subject = arguments.get("subject")
        detail = arguments.get("detail", "summaries")

        try:
            metadata_store = get_metadata_store()

            # If no subject specified, show subjects overview
            if not subject:
                all_subjects = metadata_store.get_all_subjects()

                if not all_subjects:
                    return [TextContent(
                        type="text",
                        text="The library is empty. Use 'wyrd add' to add books."
                    )]

                output_parts = ["Available subjects:\n"]
                for subj in all_subjects:
                    books = metadata_store.get_books_by_subject(subj)
                    total_chunks = sum(b.chunk_count for b in books)
                    output_parts.append(f"- {subj}: {len(books)} book(s), {total_chunks} chunks")

                output_parts.append("\nUse explore_library with subject parameter to see books in a subject.")
                return [TextContent(type="text", text="\n".join(output_parts))]

            # Filter by subject
            books = metadata_store.get_books_by_subject(subject)

            if not books:
                return [TextContent(
                    type="text",
                    text=f"No books found in subject '{subject}'."
                )]

            output_parts = [f"Subject '{subject}' contains {len(books)} book(s):\n"]

            for book in books:
                if detail == "names":
                    output_parts.append(f"- {book.title}")

                elif detail == "summaries":
                    output_parts.append(f"- {book.title} by {book.author} [{book.slug}]")

                else:  # full
                    output_parts.append(
                        f"- {book.title}\n"
                        f"  Author: {book.author}\n"
                        f"  Slug: {book.slug}\n"
                        f"  Subject: {book.subject}\n"
                        f"  Chunks: {book.chunk_count}\n"
                        f"  Added: {book.added_at.strftime('%Y-%m-%d')}\n"
                    )

            return [TextContent(type="text", text="\n".join(output_parts))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error exploring library: {e}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def run_server() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for the MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
