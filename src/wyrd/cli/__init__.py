"""Wyrd command-line interface."""

import re
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

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


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


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
    subject: str = typer.Option(None, "--subject", "-S", help="Subject/collection (e.g., 'parenting', 'networking')"),
    title: str = typer.Option(None, "--title", "-t", help="Book title (auto-detected if omitted)"),
    author: str = typer.Option(None, "--author", "-a", help="Author name (auto-detected if omitted)"),
    chunk_size: int = typer.Option(512, "--chunk-size", help="Chunk size in characters"),
    chunk_overlap: int = typer.Option(50, "--chunk-overlap", help="Overlap between chunks"),
    extract_topics: bool = typer.Option(False, "--extract-topics", "-T", help="Extract topics from content"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
) -> None:
    """Add a book to the knowledge base."""
    from wyrd.core.indexing import MetadataStore, VectorStore
    from wyrd.core.ingestion import chunk_chapter, get_embedder, parse_epub

    file_path = Path(file).expanduser().resolve()

    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(1)

    if file_path.suffix.lower() not in [".epub"]:
        console.print(f"[red]Error:[/red] Unsupported file type: {file_path.suffix}")
        console.print("[dim]Currently only .epub files are supported[/dim]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Parse the ePub
        task = progress.add_task("Parsing ePub...", total=None)
        book_content = parse_epub(file_path)
        progress.update(task, description="[green]Parsed ePub[/green]")

    # Use provided or auto-detected values
    book_title = title or book_content.title
    book_author = author or book_content.author

    # Generate slug from title if not provided
    if slug:
        book_slug = slug
    else:
        suggested_slug = slugify(book_title)
        if yes:
            book_slug = suggested_slug
        else:
            console.print(f"\n[bold]{book_title}[/bold] by {book_author}")
            book_slug = typer.prompt("Slug", default=suggested_slug)

    # Prompt for subject if not provided
    if subject:
        book_subject = subject
    else:
        if yes:
            book_subject = "general"
        else:
            book_subject = typer.prompt("Subject", default="general")

    console.print(f"\n[bold]{book_title}[/bold] by {book_author}")
    console.print(f"[dim]Slug: {book_slug}[/dim]")
    console.print(f"[dim]Subject: {book_subject}[/dim]")
    console.print(f"[dim]Chapters: {len(book_content.chapters)}[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=None)

        # Chunk the content
        progress.update(task, description="Chunking content...")
        all_chunks = []
        for chapter in book_content.chapters:
            chunks = chunk_chapter(
                chapter_content=chapter.content,
                book_slug=book_slug,
                chapter_number=chapter.number,
                chapter_title=chapter.title,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            all_chunks.extend(chunks)

        console.print(f"[dim]Chunks: {len(all_chunks)}[/dim]")

        # Generate embeddings
        progress.update(task, description="Generating embeddings...")
        embedder = get_embedder()
        chunk_texts = [c.content for c in all_chunks]
        embeddings = embedder.embed(chunk_texts)

        # Store in vector database
        progress.update(task, description="Storing vectors...")
        vector_store = VectorStore()
        vector_store.add_chunks(all_chunks, embeddings)

        # Store metadata
        progress.update(task, description="Storing metadata...")
        metadata_store = MetadataStore()
        metadata_store.add_book(
            slug=book_slug,
            title=book_title,
            author=book_author,
            subject=book_subject,
            file_path=str(file_path),
        )
        metadata_store.add_chapters(
            book_slug,
            [
                (ch.number, ch.title, ch.start_position, ch.end_position)
                for ch in book_content.chapters
            ],
        )
        metadata_store.update_chunk_count(book_slug, len(all_chunks))

        # Extract topics if requested
        if extract_topics:
            progress.update(task, description="Extracting topics...")
            from wyrd.core.topics import TopicExtractor, TopicRegistry

            extractor = TopicExtractor(max_topics=15, min_occurrences=2)
            registry = TopicRegistry()

            # Extract topics from each chunk
            chunk_data = [(c.id, c.content) for c in all_chunks]
            topic_chunks = extractor.extract_from_chunks(chunk_data, subject=book_subject)

            # Register topics and occurrences
            topic_count = 0
            for topic_id, occurrences in topic_chunks.items():
                # Create a display name from the topic ID
                display_name = topic_id.replace("-", " ").title()

                registry.add_topic(
                    topic_id=topic_id,
                    display_name=display_name,
                    subject=book_subject,
                )

                for chunk_id, relevance in occurrences:
                    registry.add_occurrence(
                        topic_id=topic_id,
                        chunk_id=chunk_id,
                        book_slug=book_slug,
                        relevance=relevance,
                    )
                topic_count += 1

            console.print(f"[dim]Topics extracted: {topic_count}[/dim]")

        progress.update(task, description="[green]Complete![/green]")

    console.print(f"\n[green]Successfully added:[/green] {book_title}")


@app.command()
def remove(
    slug: str = typer.Argument(..., help="Book slug to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a book from the knowledge base."""
    from wyrd.core.indexing import MetadataStore, VectorStore

    metadata_store = MetadataStore()
    book = metadata_store.get_book(slug)

    if not book:
        console.print(f"[red]Error:[/red] Book not found: {slug}")
        raise typer.Exit(1)

    if not force:
        console.print(f"[yellow]About to remove:[/yellow] {book.title} by {book.author}")
        console.print(f"[dim]This will delete {book.chunk_count} chunks[/dim]")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    # Remove from vector store
    vector_store = VectorStore()
    deleted_count = vector_store.delete_by_book(slug)

    # Remove from metadata store
    metadata_store.delete_book(slug)

    console.print(f"[green]Removed:[/green] {book.title} ({deleted_count} chunks deleted)")


@app.command("list")
def list_books(
    subject: str = typer.Option(None, "--subject", "-S", help="Filter by subject"),
) -> None:
    """List all books in the knowledge base."""
    from wyrd.core.indexing import MetadataStore

    metadata_store = MetadataStore()
    books = metadata_store.get_all_books(subject=subject)

    if not books:
        if subject:
            console.print(f"[dim]No books in subject '{subject}'.[/dim]")
        else:
            console.print("[dim]No books in the knowledge base.[/dim]")
        console.print("[dim]Use 'wyrd add <file.epub>' to add a book.[/dim]")
        return

    title = f"Books in '{subject}'" if subject else "Books in Knowledge Base"
    table = Table(title=title)
    table.add_column("Slug", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Author")
    table.add_column("Subject", style="magenta")
    table.add_column("Chunks", justify="right")
    table.add_column("Added", style="dim")

    for book in books:
        table.add_row(
            book.slug,
            book.title,
            book.author,
            book.subject,
            str(book.chunk_count),
            book.added_at.strftime("%Y-%m-%d"),
        )

    console.print(table)


@app.command()
def build(
    source: str = typer.Option(None, "--source", "-s", help="Rebuild only this source"),
    full: bool = typer.Option(False, "--full", help="Full rebuild (clear and regenerate)"),
) -> None:
    """Build or rebuild indexes."""
    # For MVP, this is a no-op since we build during add
    # In the future, this could rebuild from raw files or update embeddings
    if source:
        console.print(f"[yellow]Rebuilding index for:[/yellow] {source}")
    else:
        console.print("[yellow]Rebuilding all indexes[/yellow]")
    console.print("[dim]Indexes are built automatically during 'add'. This command will support rebuilding in a future version.[/dim]")


@app.command()
def serve(
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport: stdio, http, sse"),
    port: int = typer.Option(8576, "--port", "-p", help="Port for HTTP/SSE transport"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host for HTTP/SSE transport"),
) -> None:
    """Start the MCP server."""
    if transport != "stdio":
        console.print(f"[red]Error:[/red] Transport '{transport}' not yet supported")
        console.print("[dim]Only 'stdio' transport is currently available[/dim]")
        raise typer.Exit(1)

    # Don't print to stdout when running as MCP server (it would interfere with the protocol)
    # The MCP server handles all communication
    from wyrd.mcp_server import main as mcp_main
    mcp_main()


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-n", help="Maximum results"),
    source: str = typer.Option(None, "--source", "-s", help="Filter by book slug"),
    subject: str = typer.Option(None, "--subject", "-S", help="Filter by subject"),
) -> None:
    """Search the knowledge base (for testing)."""
    from wyrd.core.retrieval import search as do_search

    console.print(f"[yellow]Searching:[/yellow] {query}")
    if subject:
        console.print(f"[dim]Subject: {subject}[/dim]")
    console.print()

    book_slugs = [source] if source else None

    try:
        results = do_search(query, n_results=limit, book_slugs=book_slugs, subject=subject)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    for i, result in enumerate(results, 1):
        console.print(f"[bold cyan]{i}.[/bold cyan] {result.citation}")
        console.print(f"   [dim]Score: {result.score:.3f}[/dim]")
        excerpt = result.content[:300]
        if len(result.content) > 300:
            excerpt += "..."
        console.print(f"   {excerpt}\n")


@app.command()
def subjects() -> None:
    """List all subjects in the knowledge base."""
    from wyrd.core.indexing import MetadataStore

    metadata_store = MetadataStore()
    all_subjects = metadata_store.get_all_subjects()

    if not all_subjects:
        console.print("[dim]No subjects found.[/dim]")
        return

    console.print("[bold]Subjects:[/bold]\n")
    for subj in all_subjects:
        books = metadata_store.get_books_by_subject(subj)
        total_chunks = sum(b.chunk_count for b in books)
        console.print(f"  [magenta]{subj}[/magenta] - {len(books)} book(s), {total_chunks} chunks")


@app.command()
def topics(
    subject: str = typer.Option(None, "--subject", "-S", help="Filter by subject"),
    book: str = typer.Option(None, "--book", "-b", help="Filter by book slug"),
) -> None:
    """List all topics in the knowledge base."""
    from wyrd.core.topics import TopicRegistry

    registry = TopicRegistry()

    if book:
        all_topics = registry.get_topics_for_book(book)
        title = f"Topics in '{book}'"
    else:
        all_topics = registry.get_all_topics(subject=subject)
        title = f"Topics in '{subject}'" if subject else "All Topics"

    if not all_topics:
        console.print("[dim]No topics found.[/dim]")
        console.print("[dim]Topics are extracted when you add books with --extract-topics.[/dim]")
        return

    console.print(f"[bold]{title}:[/bold]\n")

    table = Table()
    table.add_column("Topic", style="cyan")
    table.add_column("Subject", style="magenta")
    table.add_column("Books", justify="right")
    table.add_column("Chunks", justify="right")

    for topic in all_topics:
        table.add_row(
            topic.display_name,
            topic.subject,
            str(topic.book_count),
            str(topic.chunk_count),
        )

    console.print(table)


@app.command()
def concepts(
    query: str = typer.Argument(None, help="Search for a concept"),
    book: str = typer.Option(None, "--book", "-b", help="Filter by book slug"),
    related: str = typer.Option(None, "--related", "-r", help="Show concepts related to this one"),
) -> None:
    """List or search concepts in the knowledge graph."""
    from wyrd.core.indexing import KnowledgeGraph

    graph = KnowledgeGraph()
    concept_count, edge_count = graph.count()

    if concept_count == 0:
        console.print("[dim]No concepts in the knowledge graph.[/dim]")
        console.print("[dim]Concepts can be added manually or extracted from books.[/dim]")
        return

    if related:
        # Show concepts related to a specific concept
        concept = graph.get_concept(related)
        if not concept:
            console.print(f"[red]Error:[/red] Concept '{related}' not found")
            raise typer.Exit(1)

        console.print(f"[bold]Concepts related to '{concept.display_name}':[/bold]\n")
        relations = graph.get_related_concepts(related, depth=1)

        if not relations:
            console.print("[dim]No related concepts found.[/dim]")
            return

        for rel_concept, rel_type, weight in relations:
            console.print(f"  [cyan]{rel_concept.display_name}[/cyan] ({rel_type})")
            if rel_concept.description:
                console.print(f"    [dim]{rel_concept.description}[/dim]")

    elif query:
        # Search for concepts
        results = graph.search_concepts(query)
        if not results:
            console.print(f"[dim]No concepts matching '{query}'.[/dim]")
            return

        console.print(f"[bold]Concepts matching '{query}':[/bold]\n")
        for concept in results:
            console.print(f"  [cyan]{concept.display_name}[/cyan] [{concept.id}]")
            if concept.description:
                console.print(f"    [dim]{concept.description}[/dim]")
            if concept.source_book:
                console.print(f"    [dim]Source: {concept.source_book}[/dim]")

    elif book:
        # List concepts from a specific book
        all_concepts = graph.get_concepts_by_book(book)
        if not all_concepts:
            console.print(f"[dim]No concepts found for book '{book}'.[/dim]")
            return

        console.print(f"[bold]Concepts from '{book}':[/bold]\n")
        for concept in all_concepts:
            console.print(f"  [cyan]{concept.display_name}[/cyan]")
            if concept.description:
                console.print(f"    [dim]{concept.description}[/dim]")

    else:
        # List all concepts
        all_concepts = graph.get_all_concepts()
        console.print(f"[bold]Knowledge Graph:[/bold] {concept_count} concepts, {edge_count} relationships\n")

        for concept in all_concepts[:20]:  # Limit to first 20
            console.print(f"  [cyan]{concept.display_name}[/cyan] [{concept.id}]")
            if concept.source_book:
                console.print(f"    [dim]Source: {concept.source_book}[/dim]")

        if len(all_concepts) > 20:
            console.print(f"\n[dim]...and {len(all_concepts) - 20} more. Use --query to search.[/dim]")


# Create curation subcommand group
curate_app = typer.Typer(
    name="curate",
    help="Human curation workflow commands.",
    no_args_is_help=True,
)
app.add_typer(curate_app, name="curate")


@curate_app.command("init")
def curate_init(
    slug: str = typer.Argument(..., help="Book slug to create templates for"),
    output: str = typer.Option(None, "--output", "-o", help="Output directory (default: ./knowledge/sources/{slug})"),
) -> None:
    """Generate curation templates for a book."""
    from wyrd.curation import generate_curation_template

    if output:
        book_dir = Path(output).expanduser().resolve()
    else:
        book_dir = Path("./knowledge/sources") / slug

    if book_dir.exists():
        console.print(f"[yellow]Warning:[/yellow] Directory already exists: {book_dir}")
        confirm = typer.confirm("Overwrite existing files?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    generate_curation_template(slug, book_dir)
    console.print(f"[green]Created curation templates in:[/green] {book_dir}")
    console.print("\n[dim]Edit the YAML files to add curated content, then run:[/dim]")
    console.print(f"[dim]  wyrd curate validate {book_dir}[/dim]")
    console.print(f"[dim]  wyrd curate import {book_dir}[/dim]")


@curate_app.command("validate")
def curate_validate(
    path: str = typer.Argument(..., help="Path to curation directory"),
) -> None:
    """Validate curation files for a book."""
    from wyrd.curation import format_validation_result, validate_book_directory

    book_dir = Path(path).expanduser().resolve()

    if not book_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {book_dir}")
        raise typer.Exit(1)

    result = validate_book_directory(book_dir)
    console.print(format_validation_result(result))

    if not result.valid:
        raise typer.Exit(1)


@curate_app.command("import")
def curate_import(
    path: str = typer.Argument(..., help="Path to curation directory"),
    subject: str = typer.Option("general", "--subject", "-S", help="Subject for this book"),
) -> None:
    """Import curated content into the knowledge base."""
    from wyrd.curation import CurationImporter, format_import_result

    book_dir = Path(path).expanduser().resolve()

    if not book_dir.exists():
        console.print(f"[red]Error:[/red] Directory not found: {book_dir}")
        raise typer.Exit(1)

    importer = CurationImporter()
    result = importer.import_from_directory(book_dir, subject=subject)
    console.print(format_import_result(result))

    if not result.success:
        raise typer.Exit(1)


def cli() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli()
