"""Tests for curation module."""

import pytest
from pathlib import Path

from wyrd.curation import (
    BookPhilosophy,
    CuratedBook,
    CuratedPrinciple,
    CuratedStrategy,
    CurationImporter,
    ImportResult,
    SourceCitation,
    ValidationError,
    ValidationResult,
    format_import_result,
    format_validation_result,
    generate_curation_template,
    load_curated_book,
    save_curated_book,
    validate_curated_book,
    validate_book_directory,
)


class TestSourceCitation:
    """Tests for SourceCitation dataclass."""

    def test_source_citation_creation(self):
        """SourceCitation can be created."""
        citation = SourceCitation(
            chapter="Introduction",
            location=156,
            quote="Kids are good inside.",
        )

        assert citation.chapter == "Introduction"
        assert citation.location == 156
        assert citation.quote == "Kids are good inside."

    def test_source_citation_defaults(self):
        """SourceCitation has sensible defaults."""
        citation = SourceCitation(chapter="Ch1")

        assert citation.location is None
        assert citation.quote == ""


class TestCuratedPrinciple:
    """Tests for CuratedPrinciple dataclass."""

    def test_curated_principle_creation(self):
        """CuratedPrinciple can be created."""
        principle = CuratedPrinciple(
            id="gi-principle-001",
            title="Kids are good inside",
            summary="Children's difficult behaviors are not evidence of a bad kid.",
            topics=["behavior", "discipline"],
            source=SourceCitation(chapter="Good Inside", location=156),
            concepts=["good-inside"],
        )

        assert principle.id == "gi-principle-001"
        assert len(principle.topics) == 2
        assert len(principle.concepts) == 1


class TestCuratedStrategy:
    """Tests for CuratedStrategy dataclass."""

    def test_curated_strategy_creation(self):
        """CuratedStrategy can be created."""
        strategy = CuratedStrategy(
            id="gi-strategy-001",
            title="Deep Breathing",
            summary="Use deep breaths to regulate emotions.",
            topics=["regulation"],
            source=SourceCitation(chapter="Strategies", location=500),
            steps=["Take a deep breath", "Hold for 4 counts", "Exhale slowly"],
        )

        assert strategy.id == "gi-strategy-001"
        assert len(strategy.steps) == 3


class TestBookPhilosophy:
    """Tests for BookPhilosophy dataclass."""

    def test_book_philosophy_creation(self):
        """BookPhilosophy can be created."""
        philosophy = BookPhilosophy(
            core_belief="Children are inherently good.",
            key_ideas=["Connection before correction", "Two things are true"],
            source=SourceCitation(chapter="Introduction"),
        )

        assert philosophy.core_belief == "Children are inherently good."
        assert len(philosophy.key_ideas) == 2


class TestCuratedBook:
    """Tests for CuratedBook dataclass."""

    def test_curated_book_creation(self):
        """CuratedBook can be created."""
        book = CuratedBook(
            slug="good-inside",
            title="Good Inside",
            author="Dr. Becky Kennedy",
            short_name="Good Inside",
        )

        assert book.slug == "good-inside"
        assert book.philosophy is None
        assert book.principles == []
        assert book.strategies == []


class TestLoadSaveCuratedBook:
    """Tests for loading and saving curated content."""

    def test_generate_curation_template(self, temp_dir):
        """Templates can be generated for a book."""
        book_dir = temp_dir / "test-book"
        generate_curation_template("test-book", book_dir)

        assert (book_dir / "metadata.yaml").exists()
        assert (book_dir / "philosophy.yaml").exists()
        assert (book_dir / "principles.yaml").exists()
        assert (book_dir / "strategies.yaml").exists()

    def test_load_curated_book_minimal(self, temp_dir):
        """Curated book can be loaded with just metadata."""
        book_dir = temp_dir / "test-book"
        book_dir.mkdir()

        # Write minimal metadata
        metadata = book_dir / "metadata.yaml"
        metadata.write_text("""
slug: test-book
title: Test Book
author: Test Author
short_name: Test
""")

        book = load_curated_book(book_dir)

        assert book.slug == "test-book"
        assert book.title == "Test Book"
        assert book.author == "Test Author"

    def test_load_curated_book_missing_metadata(self, temp_dir):
        """Loading without metadata raises error."""
        book_dir = temp_dir / "empty-book"
        book_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            load_curated_book(book_dir)

    def test_load_curated_book_with_principles(self, temp_dir):
        """Curated book with principles can be loaded."""
        book_dir = temp_dir / "test-book"
        book_dir.mkdir()

        (book_dir / "metadata.yaml").write_text("""
slug: test-book
title: Test Book
author: Test Author
short_name: Test
""")

        (book_dir / "principles.yaml").write_text("""
principles:
  - id: test-001
    title: Test Principle
    summary: A test principle.
    topics:
      - testing
    source:
      chapter: Chapter 1
      location: 100
""")

        book = load_curated_book(book_dir)

        assert len(book.principles) == 1
        assert book.principles[0].id == "test-001"
        assert book.principles[0].topics == ["testing"]

    def test_save_and_load_roundtrip(self, temp_dir):
        """Book can be saved and loaded back."""
        book = CuratedBook(
            slug="roundtrip-book",
            title="Roundtrip Test",
            author="Test Author",
            short_name="Roundtrip",
            principles=[
                CuratedPrinciple(
                    id="rt-001",
                    title="Test Principle",
                    summary="Summary here.",
                    topics=["testing"],
                    source=SourceCitation(chapter="Ch1", location=100),
                )
            ],
        )

        book_dir = temp_dir / "roundtrip"
        save_curated_book(book, book_dir)

        loaded = load_curated_book(book_dir)

        assert loaded.slug == "roundtrip-book"
        assert loaded.title == "Roundtrip Test"
        assert len(loaded.principles) == 1
        assert loaded.principles[0].id == "rt-001"


class TestValidation:
    """Tests for validation."""

    def test_validate_valid_book(self):
        """Valid book passes validation."""
        book = CuratedBook(
            slug="valid-book",
            title="Valid Book",
            author="Author",
            short_name="Valid",
            principles=[
                CuratedPrinciple(
                    id="valid-001",
                    title="Valid Principle",
                    summary="Summary.",
                    topics=["topic"],
                    source=SourceCitation(chapter="Ch1"),
                )
            ],
        )

        result = validate_curated_book(book)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_missing_required_fields(self):
        """Missing required fields are errors."""
        book = CuratedBook(
            slug="",  # Missing
            title="",  # Missing
            author="",
            short_name="",
        )

        result = validate_curated_book(book)

        assert result.valid is False
        assert len(result.errors) >= 2  # slug and title

    def test_validate_duplicate_ids(self):
        """Duplicate IDs are errors."""
        book = CuratedBook(
            slug="test",
            title="Test",
            author="Author",
            short_name="Test",
            principles=[
                CuratedPrinciple(
                    id="duplicate-id",
                    title="First",
                    summary="Summary",
                    topics=["topic"],
                    source=SourceCitation(chapter="Ch1"),
                ),
                CuratedPrinciple(
                    id="duplicate-id",
                    title="Second",
                    summary="Summary",
                    topics=["topic"],
                    source=SourceCitation(chapter="Ch2"),
                ),
            ],
        )

        result = validate_curated_book(book)

        assert result.valid is False
        assert any("duplicate" in e.message for e in result.errors)

    def test_validate_book_directory(self, temp_dir):
        """Directory validation works."""
        book_dir = temp_dir / "validate-book"
        book_dir.mkdir()

        (book_dir / "metadata.yaml").write_text("""
slug: validate-book
title: Validate Book
author: Author
short_name: Validate
""")

        result = validate_book_directory(book_dir)

        assert result.valid is True

    def test_validate_nonexistent_directory(self, temp_dir):
        """Nonexistent directory fails validation."""
        book_dir = temp_dir / "nonexistent"

        result = validate_book_directory(book_dir)

        assert result.valid is False

    def test_format_validation_result(self):
        """Validation result can be formatted."""
        result = ValidationResult(
            valid=False,
            errors=[ValidationError("file.yaml", "field", "is required")],
            warnings=[ValidationError("file.yaml", "other", "is empty")],
        )

        formatted = format_validation_result(result)

        assert "failed" in formatted.lower()
        assert "is required" in formatted
        assert "is empty" in formatted


class TestImporter:
    """Tests for CurationImporter."""

    def test_import_book(self, temp_dir):
        """Book can be imported into knowledge base."""
        from wyrd.core.indexing import KnowledgeGraph
        from wyrd.core.topics import TopicRegistry

        book = CuratedBook(
            slug="import-test",
            title="Import Test",
            author="Author",
            short_name="Import",
            principles=[
                CuratedPrinciple(
                    id="import-001",
                    title="Test Principle",
                    summary="Summary.",
                    topics=["testing"],
                    concepts=["test-concept"],
                    source=SourceCitation(chapter="Ch1"),
                )
            ],
        )

        topic_registry = TopicRegistry(storage_path=temp_dir / "topics.db")
        knowledge_graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        importer = CurationImporter(
            topic_registry=topic_registry,
            knowledge_graph=knowledge_graph,
        )

        result = importer.import_book(book, subject="testing")

        assert result.success is True
        assert result.principles_imported == 1
        assert result.topics_added >= 1
        assert result.concepts_added >= 1

        # Verify topic was added
        topic = topic_registry.get_topic("testing")
        assert topic is not None

        # Verify concept was added
        concept = knowledge_graph.get_concept("test-concept")
        assert concept is not None

    def test_import_with_philosophy(self, temp_dir):
        """Philosophy creates concept and relationships."""
        from wyrd.core.indexing import KnowledgeGraph

        book = CuratedBook(
            slug="philosophy-test",
            title="Philosophy Test",
            author="Author",
            short_name="Philosophy",
            philosophy=BookPhilosophy(
                core_belief="Test belief.",
                key_ideas=["Idea one", "Idea two"],
                source=SourceCitation(chapter="Intro"),
            ),
        )

        knowledge_graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        importer = CurationImporter(knowledge_graph=knowledge_graph)
        result = importer.import_book(book, subject="testing")

        assert result.success is True
        assert result.concepts_added >= 3  # Philosophy + 2 ideas

    def test_import_invalid_book(self, temp_dir):
        """Invalid book fails import with validation."""
        from wyrd.core.indexing import KnowledgeGraph

        book = CuratedBook(
            slug="",  # Invalid
            title="",  # Invalid
            author="",
            short_name="",
        )

        knowledge_graph = KnowledgeGraph(storage_path=temp_dir / "graph")
        importer = CurationImporter(knowledge_graph=knowledge_graph)

        result = importer.import_book(book, validate=True)

        assert result.success is False
        assert len(result.errors) > 0

    def test_import_from_directory(self, temp_dir):
        """Import can read from directory."""
        from wyrd.core.indexing import KnowledgeGraph

        book_dir = temp_dir / "dir-import"
        book_dir.mkdir()

        (book_dir / "metadata.yaml").write_text("""
slug: dir-import
title: Directory Import
author: Author
short_name: DirImport
""")

        (book_dir / "principles.yaml").write_text("""
principles:
  - id: dir-001
    title: Directory Principle
    summary: Summary.
    topics:
      - directory-testing
    source:
      chapter: Ch1
""")

        knowledge_graph = KnowledgeGraph(storage_path=temp_dir / "graph")
        importer = CurationImporter(knowledge_graph=knowledge_graph)

        result = importer.import_from_directory(book_dir, subject="testing")

        assert result.success is True
        assert result.principles_imported == 1

    def test_format_import_result_success(self):
        """Import result can be formatted (success)."""
        result = ImportResult(
            success=True,
            book_slug="test-book",
            principles_imported=5,
            strategies_imported=3,
            concepts_added=10,
            topics_added=8,
            errors=[],
        )

        formatted = format_import_result(result)

        assert "Successfully" in formatted
        assert "5 principles" in formatted
        assert "3 strategies" in formatted

    def test_format_import_result_failure(self):
        """Import result can be formatted (failure)."""
        result = ImportResult(
            success=False,
            book_slug="test-book",
            principles_imported=0,
            strategies_imported=0,
            concepts_added=0,
            topics_added=0,
            errors=["Error 1", "Error 2"],
        )

        formatted = format_import_result(result)

        assert "failed" in formatted.lower()
        assert "Error 1" in formatted
