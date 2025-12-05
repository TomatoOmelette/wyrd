"""Import curated content into the knowledge base."""

from dataclasses import dataclass
from pathlib import Path

from wyrd.core.indexing import KnowledgeGraph
from wyrd.core.topics import TopicRegistry
from wyrd.curation.models import CuratedBook, load_curated_book
from wyrd.curation.validator import validate_curated_book


@dataclass
class ImportResult:
    """Result of importing curated content."""

    success: bool
    book_slug: str
    principles_imported: int
    strategies_imported: int
    concepts_added: int
    topics_added: int
    errors: list[str]


class CurationImporter:
    """Import curated content into the knowledge base."""

    def __init__(
        self,
        topic_registry: TopicRegistry | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
    ):
        """
        Initialize the importer.

        Args:
            topic_registry: TopicRegistry instance
            knowledge_graph: KnowledgeGraph instance
        """
        self.topic_registry = topic_registry or TopicRegistry()
        self.knowledge_graph = knowledge_graph or KnowledgeGraph()

    def import_book(
        self,
        book: CuratedBook,
        subject: str = "general",
        validate: bool = True,
    ) -> ImportResult:
        """
        Import a curated book into the knowledge base.

        This imports:
        - Topics referenced in principles/strategies
        - Concepts into the knowledge graph
        - Relationships between concepts

        Args:
            book: The curated book to import
            subject: Subject/collection for this book
            validate: Whether to validate before importing

        Returns:
            ImportResult with statistics
        """
        errors: list[str] = []

        # Optionally validate first
        if validate:
            validation = validate_curated_book(book)
            if not validation.valid:
                error_msgs = [f"{e.field}: {e.message}" for e in validation.errors]
                return ImportResult(
                    success=False,
                    book_slug=book.slug,
                    principles_imported=0,
                    strategies_imported=0,
                    concepts_added=0,
                    topics_added=0,
                    errors=error_msgs,
                )

        topics_added = 0
        concepts_added = 0

        # Collect all topics and concepts from principles
        for principle in book.principles:
            # Add topics
            for topic_id in principle.topics:
                self.topic_registry.add_topic(
                    topic_id=topic_id,
                    display_name=topic_id.replace("-", " ").title(),
                    subject=subject,
                )
                topics_added += 1

            # Add concepts to knowledge graph
            for concept_id in principle.concepts:
                self.knowledge_graph.add_concept(
                    concept_id=concept_id,
                    display_name=concept_id.replace("-", " ").title(),
                    description=principle.summary[:200] if principle.summary else "",
                    source_book=book.slug,
                )
                concepts_added += 1

        # Collect from strategies
        for strategy in book.strategies:
            # Add topics
            for topic_id in strategy.topics:
                self.topic_registry.add_topic(
                    topic_id=topic_id,
                    display_name=topic_id.replace("-", " ").title(),
                    subject=subject,
                )
                topics_added += 1

            # Add concepts
            for concept_id in strategy.concepts:
                self.knowledge_graph.add_concept(
                    concept_id=concept_id,
                    display_name=concept_id.replace("-", " ").title(),
                    description=strategy.summary[:200] if strategy.summary else "",
                    source_book=book.slug,
                )
                concepts_added += 1

        # Add philosophy concepts if present
        if book.philosophy:
            # Create a concept for the core philosophy
            philosophy_concept = f"{book.slug}-philosophy"
            self.knowledge_graph.add_concept(
                concept_id=philosophy_concept,
                display_name=f"{book.short_name} Philosophy",
                description=book.philosophy.core_belief[:200] if book.philosophy.core_belief else "",
                source_book=book.slug,
            )
            concepts_added += 1

            # Link key ideas to the philosophy
            for i, idea in enumerate(book.philosophy.key_ideas):
                idea_concept = f"{book.slug}-idea-{i+1}"
                self.knowledge_graph.add_concept(
                    concept_id=idea_concept,
                    display_name=idea[:50],
                    description=idea,
                    source_book=book.slug,
                )
                self.knowledge_graph.add_relationship(
                    philosophy_concept,
                    idea_concept,
                    "elaborates",
                    source_book=book.slug,
                )
                concepts_added += 1

        return ImportResult(
            success=True,
            book_slug=book.slug,
            principles_imported=len(book.principles),
            strategies_imported=len(book.strategies),
            concepts_added=concepts_added,
            topics_added=topics_added,
            errors=errors,
        )

    def import_from_directory(
        self,
        book_dir: Path,
        subject: str = "general",
    ) -> ImportResult:
        """
        Import curated content from a directory.

        Args:
            book_dir: Path to the book's curation directory
            subject: Subject/collection for this book

        Returns:
            ImportResult with statistics
        """
        try:
            book = load_curated_book(book_dir)
            return self.import_book(book, subject)
        except FileNotFoundError as e:
            return ImportResult(
                success=False,
                book_slug=book_dir.name,
                principles_imported=0,
                strategies_imported=0,
                concepts_added=0,
                topics_added=0,
                errors=[str(e)],
            )
        except Exception as e:
            return ImportResult(
                success=False,
                book_slug=book_dir.name,
                principles_imported=0,
                strategies_imported=0,
                concepts_added=0,
                topics_added=0,
                errors=[f"Import failed: {e}"],
            )


def format_import_result(result: ImportResult) -> str:
    """Format import result as readable text."""
    if result.success:
        return (
            f"Successfully imported '{result.book_slug}':\n"
            f"  - {result.principles_imported} principles\n"
            f"  - {result.strategies_imported} strategies\n"
            f"  - {result.concepts_added} concepts added to graph\n"
            f"  - {result.topics_added} topics registered"
        )
    else:
        error_list = "\n  - ".join(result.errors)
        return f"Import failed for '{result.book_slug}':\n  - {error_list}"
