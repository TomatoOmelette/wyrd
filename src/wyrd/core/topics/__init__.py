"""Topic extraction and management."""

from wyrd.core.topics.extractor import TopicExtractor, extract_topics
from wyrd.core.topics.registry import Topic, TopicRegistry

__all__ = [
    "TopicExtractor",
    "extract_topics",
    "Topic",
    "TopicRegistry",
]
