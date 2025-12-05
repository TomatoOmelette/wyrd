"""Rule-based synthesis for retrieved content."""

from dataclasses import dataclass
from difflib import SequenceMatcher

from wyrd.core.retrieval import SearchResult


@dataclass
class SynthesizedAdvice:
    """Synthesized advice from multiple sources."""

    question: str
    summary: str
    key_points: list[str]
    citations: list[str]
    source_count: int
    chunk_count: int


@dataclass
class SourcePerspective:
    """A source's perspective on a topic."""

    book_title: str
    book_author: str
    book_slug: str
    key_points: list[str]
    citations: list[str]


@dataclass
class SourceComparison:
    """Comparison of multiple sources on a topic."""

    topic: str
    perspectives: list[SourcePerspective]
    agreements: list[str]
    differences: list[str]
    source_count: int


class Synthesizer:
    """Rule-based synthesis of retrieved content.

    This synthesizer uses simple extraction and deduplication rules
    to condense retrieved chunks into a coherent response. No LLM required.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.7,
        max_points_per_source: int = 3,
        max_total_points: int = 10,
    ):
        """
        Initialize the synthesizer.

        Args:
            similarity_threshold: Threshold for considering content duplicate (0-1)
            max_points_per_source: Maximum key points to extract per source
            max_total_points: Maximum total key points in output
        """
        self.similarity_threshold = similarity_threshold
        self.max_points_per_source = max_points_per_source
        self.max_total_points = max_total_points

    def _extract_sentences(self, text: str) -> list[str]:
        """Extract sentences from text."""
        # Simple sentence splitting
        sentences = []
        current = []

        for char in text:
            current.append(char)
            if char in ".!?" and len(current) > 20:
                sentence = "".join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []

        # Don't forget the last part
        if current:
            sentence = "".join(current).strip()
            if sentence and len(sentence) > 20:
                sentences.append(sentence)

        return sentences

    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _is_duplicate(self, sentence: str, existing: list[str]) -> bool:
        """Check if a sentence is too similar to existing ones."""
        for existing_sentence in existing:
            if self._similarity(sentence, existing_sentence) > self.similarity_threshold:
                return True
        return False

    def _extract_key_points(
        self,
        results: list[SearchResult],
        max_points: int,
    ) -> tuple[list[str], list[str]]:
        """
        Extract key points from results, deduplicating similar content.

        Returns:
            Tuple of (key_points, citations)
        """
        key_points = []
        citations = []
        seen_citations = set()

        for result in results:
            sentences = self._extract_sentences(result.content)

            for sentence in sentences[:self.max_points_per_source]:
                if len(key_points) >= max_points:
                    break

                if not self._is_duplicate(sentence, key_points):
                    key_points.append(sentence)

                    # Add citation if not seen
                    citation = result.citation
                    if citation not in seen_citations:
                        citations.append(citation)
                        seen_citations.add(citation)

            if len(key_points) >= max_points:
                break

        return key_points, citations

    def synthesize(
        self,
        question: str,
        results: list[SearchResult],
    ) -> SynthesizedAdvice:
        """
        Synthesize advice from search results.

        Args:
            question: The original question
            results: Search results to synthesize

        Returns:
            SynthesizedAdvice with key points and citations
        """
        if not results:
            return SynthesizedAdvice(
                question=question,
                summary="No relevant information found in the knowledge base.",
                key_points=[],
                citations=[],
                source_count=0,
                chunk_count=0,
            )

        # Extract key points
        key_points, citations = self._extract_key_points(
            results, self.max_total_points
        )

        # Count unique sources
        source_slugs = {r.book_slug for r in results}

        # Create summary from top key points
        if key_points:
            summary = " ".join(key_points[:3])
            if len(summary) > 500:
                summary = summary[:497] + "..."
        else:
            summary = "Found relevant passages but could not extract key points."

        return SynthesizedAdvice(
            question=question,
            summary=summary,
            key_points=key_points,
            citations=citations,
            source_count=len(source_slugs),
            chunk_count=len(results),
        )

    def synthesize_by_source(
        self,
        question: str,
        results: list[SearchResult],
    ) -> list[SourcePerspective]:
        """
        Synthesize results grouped by source.

        Args:
            question: The original question
            results: Search results to synthesize

        Returns:
            List of SourcePerspective, one per book
        """
        # Group by book
        by_book: dict[str, list[SearchResult]] = {}
        for result in results:
            if result.book_slug not in by_book:
                by_book[result.book_slug] = []
            by_book[result.book_slug].append(result)

        perspectives = []
        for book_slug, book_results in by_book.items():
            if not book_results:
                continue

            first = book_results[0]
            key_points, citations = self._extract_key_points(
                book_results, self.max_points_per_source
            )

            perspectives.append(
                SourcePerspective(
                    book_title=first.book_title,
                    book_author=first.book_author,
                    book_slug=book_slug,
                    key_points=key_points,
                    citations=citations,
                )
            )

        return perspectives

    def compare_sources(
        self,
        topic: str,
        results: list[SearchResult],
    ) -> SourceComparison:
        """
        Compare how different sources approach a topic.

        Args:
            topic: The topic being compared
            results: Search results from multiple sources

        Returns:
            SourceComparison with agreements and differences
        """
        perspectives = self.synthesize_by_source(topic, results)

        if len(perspectives) < 2:
            return SourceComparison(
                topic=topic,
                perspectives=perspectives,
                agreements=[],
                differences=[],
                source_count=len(perspectives),
            )

        # Find agreements (similar key points across sources)
        agreements = []
        all_points = []
        for p in perspectives:
            all_points.extend(p.key_points)

        # Look for points that appear similarly in multiple sources
        for i, point in enumerate(all_points):
            for j, other in enumerate(all_points[i + 1 :], i + 1):
                if self._similarity(point, other) > 0.5:  # Lower threshold for "related"
                    agreement = f"Multiple sources emphasize: {point[:100]}..."
                    if not self._is_duplicate(agreement, agreements):
                        agreements.append(agreement)

        # Find differences (unique approaches)
        differences = []
        for p in perspectives:
            for point in p.key_points[:2]:  # Top 2 points per source
                # Check if this point is unique to this source
                is_unique = True
                for other_p in perspectives:
                    if other_p.book_slug == p.book_slug:
                        continue
                    for other_point in other_p.key_points:
                        if self._similarity(point, other_point) > 0.5:
                            is_unique = False
                            break
                    if not is_unique:
                        break

                if is_unique:
                    diff = f"{p.book_title} uniquely emphasizes: {point[:100]}..."
                    if not self._is_duplicate(diff, differences):
                        differences.append(diff)

        return SourceComparison(
            topic=topic,
            perspectives=perspectives,
            agreements=agreements[:5],  # Limit agreements
            differences=differences[:5],  # Limit differences
            source_count=len(perspectives),
        )


def format_advice(advice: SynthesizedAdvice) -> str:
    """Format synthesized advice as readable text."""
    parts = []

    parts.append(f"Question: {advice.question}\n")
    parts.append(f"Summary: {advice.summary}\n")

    if advice.key_points:
        parts.append("\nKey Points:")
        for i, point in enumerate(advice.key_points, 1):
            parts.append(f"  {i}. {point}")

    if advice.citations:
        parts.append("\nSources:")
        for citation in advice.citations:
            parts.append(f"  - {citation}")

    parts.append(f"\n(Based on {advice.chunk_count} passages from {advice.source_count} source(s))")

    return "\n".join(parts)


def format_comparison(comparison: SourceComparison) -> str:
    """Format source comparison as readable text."""
    parts = []

    parts.append(f"Topic: {comparison.topic}\n")
    parts.append(f"Comparing {comparison.source_count} source(s):\n")

    for p in comparison.perspectives:
        parts.append(f"\n{p.book_title} by {p.book_author}:")
        for point in p.key_points:
            parts.append(f"  - {point[:150]}...")

    if comparison.agreements:
        parts.append("\nAgreements:")
        for agreement in comparison.agreements:
            parts.append(f"  - {agreement}")

    if comparison.differences:
        parts.append("\nUnique Perspectives:")
        for diff in comparison.differences:
            parts.append(f"  - {diff}")

    return "\n".join(parts)
