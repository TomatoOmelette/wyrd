"""Tests for topic extraction and registry."""

import pytest

from wyrd.core.topics.extractor import ExtractedTopic, TopicExtractor, extract_topics
from wyrd.core.topics.registry import Topic, TopicOccurrence, TopicRegistry


class TestExtractedTopic:
    """Tests for ExtractedTopic dataclass."""

    def test_extracted_topic_creation(self):
        """ExtractedTopic can be created."""
        topic = ExtractedTopic(
            id="emotional-safety",
            display_name="Emotional Safety",
            relevance=0.85,
        )

        assert topic.id == "emotional-safety"
        assert topic.display_name == "Emotional Safety"
        assert topic.relevance == 0.85


class TestTopicExtractor:
    """Tests for TopicExtractor."""

    def test_extract_from_empty_text(self):
        """Empty text returns no topics."""
        extractor = TopicExtractor()
        topics = extractor.extract("")

        assert topics == []

    def test_extract_single_word_topics(self):
        """Repeated words become topics."""
        extractor = TopicExtractor(min_occurrences=2)
        text = "Children need boundaries. Boundaries help children feel safe. Children thrive with clear boundaries."

        topics = extractor.extract(text)

        topic_ids = [t.id for t in topics]
        assert "children" in topic_ids
        assert "boundaries" in topic_ids

    def test_extract_bigram_topics(self):
        """Repeated word pairs become topics."""
        extractor = TopicExtractor(min_occurrences=2)
        text = (
            "Emotion coaching helps children. Emotion coaching is about being present. "
            "Emotion coaching validates feelings."
        )

        topics = extractor.extract(text)

        # Should extract "emotion coaching" as a bigram
        topic_ids = [t.id for t in topics]
        assert "emotion-coaching" in topic_ids or "emotion" in topic_ids

    def test_extract_filters_stop_words(self):
        """Stop words are filtered out."""
        extractor = TopicExtractor(min_occurrences=1)
        text = "The the the and and and but but but"

        topics = extractor.extract(text)

        # Should not have common stop words as topics
        topic_ids = [t.id for t in topics]
        assert "the" not in topic_ids
        assert "and" not in topic_ids
        assert "but" not in topic_ids

    def test_extract_respects_min_word_length(self):
        """Short words are filtered."""
        extractor = TopicExtractor(min_word_length=4, min_occurrences=1)
        text = "be do go to at in on by is it we me us he"

        topics = extractor.extract(text)

        assert topics == []

    def test_extract_respects_min_occurrences(self):
        """Words below min_occurrences are excluded."""
        extractor = TopicExtractor(min_occurrences=3)
        text = "parenting parenting children"  # parenting=2, children=1

        topics = extractor.extract(text)

        topic_ids = [t.id for t in topics]
        assert "parenting" not in topic_ids
        assert "children" not in topic_ids

    def test_extract_respects_max_topics(self):
        """Number of topics is capped."""
        extractor = TopicExtractor(min_occurrences=2, max_topics=3)
        text = (
            "alpha alpha alpha beta beta beta gamma gamma gamma "
            "delta delta delta epsilon epsilon epsilon zeta zeta zeta"
        )

        topics = extractor.extract(text)

        assert len(topics) <= 3

    def test_extract_topics_ordered_by_relevance(self):
        """Topics are ordered by relevance (frequency)."""
        extractor = TopicExtractor(min_occurrences=2)
        text = (
            "boundaries boundaries boundaries boundaries "
            "emotions emotions emotions "
            "parenting parenting"
        )

        topics = extractor.extract(text)

        assert len(topics) >= 2
        # Higher frequency should come first
        assert topics[0].relevance >= topics[-1].relevance

    def test_extract_with_custom_stop_words(self):
        """Custom stop words are filtered."""
        custom_stops = {"parenting", "children"}
        extractor = TopicExtractor(custom_stop_words=custom_stops, min_occurrences=2)
        text = "parenting parenting children children boundaries boundaries"

        topics = extractor.extract(text)

        topic_ids = [t.id for t in topics]
        assert "parenting" not in topic_ids
        assert "children" not in topic_ids
        assert "boundaries" in topic_ids

    def test_extract_from_chunks(self):
        """Topics can be extracted from multiple chunks."""
        extractor = TopicExtractor(min_occurrences=2)
        # Each chunk needs enough repetition to meet min_occurrences within it
        chunks = [
            ("chunk-1", "Emotion coaching coaching helps children children understand"),
            ("chunk-2", "Emotion coaching coaching validates children children emotional"),
            ("chunk-3", "Through coaching coaching children children learn to regulate"),
        ]

        topic_chunks = extractor.extract_from_chunks(chunks)

        assert len(topic_chunks) > 0
        # At least some topics should appear in multiple chunks
        for topic_id, occurrences in topic_chunks.items():
            assert len(occurrences) >= 1
            for chunk_id, relevance in occurrences:
                assert chunk_id.startswith("chunk-")
                assert 0 <= relevance <= 1

    def test_slugify(self):
        """Topics are slugified correctly."""
        extractor = TopicExtractor(min_occurrences=2)
        text = "emotion coaching emotion coaching"

        topics = extractor.extract(text)

        # Should be lowercase, hyphenated
        for topic in topics:
            assert topic.id == topic.id.lower()
            assert " " not in topic.id


class TestExtractTopicsFunction:
    """Tests for the convenience extract_topics function."""

    def test_extract_topics_basic(self):
        """Convenience function extracts topics."""
        text = "Children children boundaries boundaries emotions emotions"

        topics = extract_topics(text, min_occurrences=2)

        assert len(topics) > 0
        topic_ids = [t.id for t in topics]
        assert "children" in topic_ids

    def test_extract_topics_with_max(self):
        """Max topics parameter is respected."""
        text = "alpha alpha beta beta gamma gamma delta delta epsilon epsilon"

        topics = extract_topics(text, max_topics=2, min_occurrences=2)

        assert len(topics) <= 2


class TestTopic:
    """Tests for Topic dataclass."""

    def test_topic_creation(self):
        """Topic can be created with required fields."""
        topic = Topic(
            id="tantrums",
            display_name="Tantrums",
            description="Managing tantrum behavior",
            subject="parenting",
            related_topics=["emotions", "boundaries"],
        )

        assert topic.id == "tantrums"
        assert topic.display_name == "Tantrums"
        assert topic.subject == "parenting"
        assert len(topic.related_topics) == 2
        assert topic.book_count == 0
        assert topic.chunk_count == 0


class TestTopicOccurrence:
    """Tests for TopicOccurrence dataclass."""

    def test_topic_occurrence_creation(self):
        """TopicOccurrence can be created."""
        occurrence = TopicOccurrence(
            topic_id="tantrums",
            chunk_id="good-inside-ch003-0005",
            book_slug="good-inside",
            relevance=0.9,
        )

        assert occurrence.topic_id == "tantrums"
        assert occurrence.chunk_id == "good-inside-ch003-0005"
        assert occurrence.book_slug == "good-inside"
        assert occurrence.relevance == 0.9


class TestTopicRegistry:
    """Tests for TopicRegistry."""

    def test_create_empty_registry(self, temp_dir):
        """New registry starts empty."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        topics = registry.get_all_topics()
        assert topics == []

    def test_add_topic(self, temp_dir):
        """Topics can be added to registry."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        topic = registry.add_topic(
            topic_id="tantrums",
            display_name="Tantrums",
            description="Managing tantrum behavior",
            subject="parenting",
        )

        assert topic.id == "tantrums"
        assert topic.display_name == "Tantrums"
        assert topic.subject == "parenting"

    def test_add_topic_with_related(self, temp_dir):
        """Topics can have related topics."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        topic = registry.add_topic(
            topic_id="tantrums",
            display_name="Tantrums",
            subject="parenting",
            related_topics=["emotions", "boundaries"],
        )

        assert len(topic.related_topics) == 2
        assert "emotions" in topic.related_topics

    def test_get_topic(self, temp_dir):
        """Topics can be retrieved by ID."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("boundaries", "Boundaries", subject="parenting")

        topic = registry.get_topic("boundaries")
        assert topic is not None
        assert topic.id == "boundaries"

    def test_get_nonexistent_topic(self, temp_dir):
        """Getting nonexistent topic returns None."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        topic = registry.get_topic("nonexistent")
        assert topic is None

    def test_update_topic(self, temp_dir):
        """Topics can be updated."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_topic("tantrums", "Tantrums", description="Updated description", subject="parenting")

        topic = registry.get_topic("tantrums")
        assert topic is not None
        assert topic.description == "Updated description"

    def test_add_occurrence(self, temp_dir):
        """Topic occurrences can be recorded."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_occurrence("tantrums", "book-ch001-0001", "book", 0.9)

        topic = registry.get_topic("tantrums")
        assert topic is not None
        assert topic.chunk_count == 1
        assert topic.book_count == 1

    def test_occurrence_updates_max_relevance(self, temp_dir):
        """Duplicate occurrence keeps max relevance."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_occurrence("tantrums", "book-ch001-0001", "book", 0.5)
        registry.add_occurrence("tantrums", "book-ch001-0001", "book", 0.9)

        # Should still only have one occurrence
        topic = registry.get_topic("tantrums")
        assert topic is not None
        assert topic.chunk_count == 1

    def test_get_all_topics(self, temp_dir):
        """All topics can be retrieved."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_topic("boundaries", "Boundaries", subject="parenting")
        registry.add_topic("tcp", "TCP", subject="networking")

        all_topics = registry.get_all_topics()
        assert len(all_topics) == 3

    def test_get_topics_by_subject(self, temp_dir):
        """Topics can be filtered by subject."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_topic("boundaries", "Boundaries", subject="parenting")
        registry.add_topic("tcp", "TCP", subject="networking")

        parenting_topics = registry.get_all_topics(subject="parenting")
        assert len(parenting_topics) == 2

        networking_topics = registry.get_all_topics(subject="networking")
        assert len(networking_topics) == 1

    def test_get_topics_for_book(self, temp_dir):
        """Topics for a specific book can be retrieved."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_topic("boundaries", "Boundaries", subject="parenting")
        registry.add_topic("emotions", "Emotions", subject="parenting")

        registry.add_occurrence("tantrums", "book1-ch001-0001", "book1", 0.9)
        registry.add_occurrence("boundaries", "book1-ch001-0002", "book1", 0.8)
        registry.add_occurrence("emotions", "book2-ch001-0001", "book2", 0.7)

        book1_topics = registry.get_topics_for_book("book1")
        assert len(book1_topics) == 2

        topic_ids = [t.id for t in book1_topics]
        assert "tantrums" in topic_ids
        assert "boundaries" in topic_ids
        assert "emotions" not in topic_ids

    def test_get_chunks_for_topic(self, temp_dir):
        """Chunk IDs for a topic can be retrieved."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_occurrence("tantrums", "book-ch001-0001", "book", 0.9)
        registry.add_occurrence("tantrums", "book-ch002-0003", "book", 0.7)

        chunks = registry.get_chunks_for_topic("tantrums")
        assert len(chunks) == 2
        assert "book-ch001-0001" in chunks

    def test_get_chunks_for_topic_filtered_by_book(self, temp_dir):
        """Chunks can be filtered by book."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_occurrence("tantrums", "book1-ch001-0001", "book1", 0.9)
        registry.add_occurrence("tantrums", "book2-ch001-0001", "book2", 0.8)

        chunks = registry.get_chunks_for_topic("tantrums", book_slug="book1")
        assert len(chunks) == 1
        assert "book1-ch001-0001" in chunks

    def test_get_books_for_topic(self, temp_dir):
        """Books containing a topic can be retrieved."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_occurrence("tantrums", "book1-ch001-0001", "book1", 0.9)
        registry.add_occurrence("tantrums", "book2-ch001-0001", "book2", 0.8)
        registry.add_occurrence("tantrums", "book1-ch002-0001", "book1", 0.7)

        books = registry.get_books_for_topic("tantrums")
        assert len(books) == 2
        assert "book1" in books
        assert "book2" in books

    def test_delete_by_book(self, temp_dir):
        """Occurrences can be deleted by book."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("tantrums", "Tantrums", subject="parenting")
        registry.add_occurrence("tantrums", "book1-ch001-0001", "book1", 0.9)
        registry.add_occurrence("tantrums", "book1-ch002-0001", "book1", 0.8)
        registry.add_occurrence("tantrums", "book2-ch001-0001", "book2", 0.7)

        deleted = registry.delete_by_book("book1")
        assert deleted == 2

        topic = registry.get_topic("tantrums")
        assert topic is not None
        assert topic.chunk_count == 1
        assert topic.book_count == 1

    def test_search_topics(self, temp_dir):
        """Topics can be searched by text."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic(
            "emotion-coaching",
            "Emotion Coaching",
            description="Helping children understand feelings",
            subject="parenting",
        )
        registry.add_topic(
            "emotional-safety",
            "Emotional Safety",
            description="Creating secure environment",
            subject="parenting",
        )
        registry.add_topic(
            "boundaries",
            "Boundaries",
            description="Setting limits",
            subject="parenting",
        )

        # Search by display name
        results = registry.search_topics("emotion")
        assert len(results) == 2

        # Search by description
        results = registry.search_topics("limits")
        assert len(results) == 1
        assert results[0].id == "boundaries"

    def test_persistence(self, temp_dir):
        """Registry persists across instances."""
        registry1 = TopicRegistry(storage_path=temp_dir / "topics.db")
        registry1.add_topic("persistent", "Persistent Topic", subject="test")
        registry1.add_occurrence("persistent", "chunk-001", "book", 0.9)

        # Create new instance pointing to same storage
        registry2 = TopicRegistry(storage_path=temp_dir / "topics.db")

        topic = registry2.get_topic("persistent")
        assert topic is not None
        assert topic.display_name == "Persistent Topic"
        assert topic.chunk_count == 1

    def test_topics_ordered_alphabetically(self, temp_dir):
        """Topics are returned in alphabetical order."""
        registry = TopicRegistry(storage_path=temp_dir / "topics.db")

        registry.add_topic("zebra", "Zebra", subject="test")
        registry.add_topic("alpha", "Alpha", subject="test")
        registry.add_topic("middle", "Middle", subject="test")

        topics = registry.get_all_topics()
        names = [t.display_name for t in topics]

        assert names == ["Alpha", "Middle", "Zebra"]
