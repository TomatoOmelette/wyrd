"""Wyrd command-line interface."""

import typer
from rich.console import Console

from wyrd import __version__

app = typer.Typer(
    name="wyrd",
    help="Personal book knowledge system with semantic search and MCP integration.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"wyrd version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Wyrd: The web of knowledge, interconnected like fate itself."""
    pass


@app.command()
def add(
    file: str = typer.Argument(..., help="Path to ePub or PDF file"),
    slug: str = typer.Option(None, "--slug", "-s", help="URL-friendly identifier"),
    title: str = typer.Option(None, "--title", "-t", help="Book title (auto-detected if omitted)"),
    author: str = typer.Option(None, "--author", "-a", help="Author name (auto-detected if omitted)"),
) -> None:
    """Add a book to the knowledge base."""
    console.print(f"[yellow]Adding book:[/yellow] {file}")
    console.print("[dim]Not yet implemented[/dim]")
    # TODO: Implement book ingestion


@app.command()
def remove(
    slug: str = typer.Argument(..., help="Book slug to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a book from the knowledge base."""
    console.print(f"[yellow]Removing book:[/yellow] {slug}")
    console.print("[dim]Not yet implemented[/dim]")
    # TODO: Implement book removal


@app.command("list")
def list_books() -> None:
    """List all books in the knowledge base."""
    console.print("[yellow]Books in knowledge base:[/yellow]")
    console.print("[dim]Not yet implemented[/dim]")
    # TODO: Implement book listing


@app.command()
def build(
    source: str = typer.Option(None, "--source", "-s", help="Rebuild only this source"),
    full: bool = typer.Option(False, "--full", help="Full rebuild (clear and regenerate)"),
) -> None:
    """Build or rebuild indexes."""
    if source:
        console.print(f"[yellow]Rebuilding index for:[/yellow] {source}")
    else:
        console.print("[yellow]Rebuilding all indexes[/yellow]")
    console.print("[dim]Not yet implemented[/dim]")
    # TODO: Implement index building


@app.command()
def serve(
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport: stdio, http, sse"),
    port: int = typer.Option(8576, "--port", "-p", help="Port for HTTP/SSE transport"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host for HTTP/SSE transport"),
) -> None:
    """Start the MCP server."""
    console.print(f"[green]Starting Wyrd MCP server[/green] (transport: {transport})")
    if transport in ("http", "sse"):
        console.print(f"[dim]Listening on {host}:{port}[/dim]")
    console.print("[dim]Not yet implemented[/dim]")
    # TODO: Implement MCP server


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-n", help="Maximum results"),
) -> None:
    """Search the knowledge base (for testing)."""
    console.print(f"[yellow]Searching:[/yellow] {query}")
    console.print("[dim]Not yet implemented[/dim]")
    # TODO: Implement search


@app.command()
def topics() -> None:
    """List all topics in the knowledge base."""
    console.print("[yellow]Topics:[/yellow]")
    console.print("[dim]Not yet implemented[/dim]")
    # TODO: Implement topic listing


@app.command()
def concepts() -> None:
    """List all concepts in the knowledge graph."""
    console.print("[yellow]Concepts:[/yellow]")
    console.print("[dim]Not yet implemented[/dim]")
    # TODO: Implement concept listing


if __name__ == "__main__":
    main()
