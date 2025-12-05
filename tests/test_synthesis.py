"""Tests for synthesis module."""

import pytest

from wyrd.core.retrieval import SearchResult
from wyrd.core.synthesis import (
    SourceComparison,
    SourcePerspective,
    SynthesizedAdvice,
    Synthesizer,
    format_advice,
    format_comparison,
)


def make_result(
    content: str,
    book_slug: str = "test-book",
    book_title: str = "Test Book",
    book_author: str = "Test Author",
    chapter_number: int = 1,
    score: float = 0.9,
) -> SearchResult:
    """Helper to create SearchResult for testing."""
    return SearchResult(
        chunk_id=f"{book_slug}-ch{chapter_number:03d}-0000",
        content=content,
        book_slug=book_slug,
        book_title=book_title,
        book_author=book_author,
        chapter_number=chapter_number,
        chapter_title=f"Chapter {chapter_number}",
        start_position=0,
        end_position=len(content),
        score=score,
    )


class TestSynthesizedAdvice:
    """Tests for SynthesizedAdvice dataclass."""

    def test_synthesized_advice_creation(self):
        """SynthesizedAdvice can be created."""
        advice = SynthesizedAdvice(
            question="How to handle tantrums?",
            summary="Stay calm and validate feelings.",
            key_points=["Point 1", "Point 2"],
            citations=["[Book, Ch. 1]"],
            source_count=1,
            chunk_count=3,
        )

        assert advice.question == "How to handle tantrums?"
        assert len(advice.key_points) == 2
        assert advice.source_count == 1


class TestSourcePerspective:
    """Tests for SourcePerspective dataclass."""

    def test_source_perspective_creation(self):
        """SourcePerspective can be created."""
        perspective = SourcePerspective(
            book_title="Good Inside",
            book_author="Dr. Becky Kennedy",
            book_slug="good-inside",
            key_points=["Point 1", "Point 2"],
            citations=["[Good Inside, Ch. 1]"],
        )

        assert perspective.book_title == "Good Inside"
        assert len(perspective.key_points) == 2


class TestSynthesizer:
    """Tests for Synthesizer."""

    def test_synthesize_empty_results(self):
        """Synthesizing empty results returns appropriate message."""
        synthesizer = Synthesizer()
        advice = synthesizer.synthesize("How to handle tantrums?", [])

        assert "No relevant information" in advice.summary
        assert advice.source_count == 0
        assert advice.chunk_count == 0

    def test_synthesize_single_result(self):
        """Synthesizing single result extracts key points."""
        synthesizer = Synthesizer()
        results = [
            make_result(
                "Children need boundaries. Boundaries help children feel safe. "
                "When children know the limits, they can relax.",
            )
        ]

        advice = synthesizer.synthesize("How to set boundaries?", results)

        assert advice.question == "How to set boundaries?"
        assert advice.source_count == 1
        assert advice.chunk_count == 1
        assert len(advice.key_points) > 0

    def test_synthesize_multiple_results(self):
        """Synthesizing multiple results combines and deduplicates."""
        synthesizer = Synthesizer()
        results = [
            make_result(
                "Stay calm during tantrums. Your calm is contagious.",
                book_slug="book1",
                book_title="Book One",
            ),
            make_result(
                "Validate the child's feelings. They need to feel heard.",
                book_slug="book2",
                book_title="Book Two",
            ),
        ]

        advice = synthesizer.synthesize("How to handle tantrums?", results)

        assert advice.source_count == 2
        assert advice.chunk_count == 2
        assert len(advice.citations) == 2

    def test_synthesize_deduplicates_similar_content(self):
        """Synthesizer removes duplicate or very similar content."""
        synthesizer = Synthesizer(similarity_threshold=0.7)
        results = [
            make_result("Children are good inside. Kids are good inside."),
            make_result("Children are good inside. They are good inside."),
        ]

        advice = synthesizer.synthesize("What is the core belief?", results)

        # Should deduplicate, not have both nearly identical points
        assert len(advice.key_points) < 4

    def test_synthesize_by_source(self):
        """Synthesize can group results by source."""
        synthesizer = Synthesizer()
        results = [
            make_result(
                "Book one says this about emotions.",
                book_slug="book1",
                book_title="Book One",
                book_author="Author One",
            ),
            make_result(
                "Book two says something different about emotions.",
                book_slug="book2",
                book_title="Book Two",
                book_author="Author Two",
            ),
        ]

        perspectives = synthesizer.synthesize_by_source("emotions", results)

        assert len(perspectives) == 2
        book_titles = [p.book_title for p in perspectives]
        assert "Book One" in book_titles
        assert "Book Two" in book_titles

    def test_synthesize_by_source_empty(self):
        """Synthesize by source handles empty results."""
        synthesizer = Synthesizer()
        perspectives = synthesizer.synthesize_by_source("topic", [])

        assert perspectives == []

    def test_compare_sources(self):
        """Compare sources finds agreements and differences."""
        synthesizer = Synthesizer()
        results = [
            make_result(
                "Validate feelings first. Validation is key. Always validate.",
                book_slug="book1",
                book_title="Book One",
            ),
            make_result(
                "Validate the child's emotions. Validation helps them feel heard.",
                book_slug="book2",
                book_title="Book Two",
            ),
        ]

        comparison = synthesizer.compare_sources("validation", results)

        assert comparison.topic == "validation"
        assert comparison.source_count == 2
        assert len(comparison.perspectives) == 2

    def test_compare_sources_needs_multiple_sources(self):
        """Compare sources handles single source gracefully."""
        synthesizer = Synthesizer()
        results = [
            make_result("Only one book talks about this topic."),
        ]

        comparison = synthesizer.compare_sources("topic", results)

        assert comparison.source_count == 1
        assert len(comparison.agreements) == 0
        assert len(comparison.differences) == 0


class TestFormatAdvice:
    """Tests for format_advice function."""

    def test_format_advice_basic(self):
        """Format advice produces readable output."""
        advice = SynthesizedAdvice(
            question="How to handle tantrums?",
            summary="Stay calm and validate.",
            key_points=["Stay calm", "Validate feelings"],
            citations=["[Book, Ch. 1]"],
            source_count=1,
            chunk_count=2,
        )

        formatted = format_advice(advice)

        assert "How to handle tantrums?" in formatted
        assert "Stay calm" in formatted
        assert "Validate feelings" in formatted
        assert "[Book, Ch. 1]" in formatted
        assert "1 source" in formatted

    def test_format_advice_empty_points(self):
        """Format advice handles no key points."""
        advice = SynthesizedAdvice(
            question="Test question",
            summary="No results",
            key_points=[],
            citations=[],
            source_count=0,
            chunk_count=0,
        )

        formatted = format_advice(advice)

        assert "Test question" in formatted
        assert "No results" in formatted


class TestFormatComparison:
    """Tests for format_comparison function."""

    def test_format_comparison_basic(self):
        """Format comparison produces readable output."""
        comparison = SourceComparison(
            topic="tantrums",
            perspectives=[
                SourcePerspective(
                    book_title="Book One",
                    book_author="Author One",
                    book_slug="book1",
                    key_points=["Stay calm"],
                    citations=["[Book One, Ch. 1]"],
                ),
                SourcePerspective(
                    book_title="Book Two",
                    book_author="Author Two",
                    book_slug="book2",
                    key_points=["Validate feelings"],
                    citations=["[Book Two, Ch. 2]"],
                ),
            ],
            agreements=["Both emphasize validation"],
            differences=["Book One focuses on calm"],
            source_count=2,
        )

        formatted = format_comparison(comparison)

        assert "tantrums" in formatted
        assert "Book One" in formatted
        assert "Book Two" in formatted
        assert "Agreements" in formatted
        assert "Unique Perspectives" in formatted
