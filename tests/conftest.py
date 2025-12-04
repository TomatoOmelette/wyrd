"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest

from wyrd.core.indexing import MetadataStore, VectorStore
from wyrd.core.ingestion import Chunk


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def vector_store(temp_dir):
    """Create a vector store in a temporary directory."""
    return VectorStore(storage_path=temp_dir / "vectors")


@pytest.fixture
def metadata_store(temp_dir):
    """Create a metadata store in a temporary directory."""
    return MetadataStore(storage_path=temp_dir / "metadata.db")


@pytest.fixture
def sample_chunks():
    """Create sample chunks for testing."""
    return [
        Chunk(
            id="test-book-ch001-0000",
            content="Children are good inside. When they act out, it's not because they're bad.",
            book_slug="test-book",
            chapter_number=1,
            chapter_title="Introduction",
            start_position=0,
            end_position=80,
        ),
        Chunk(
            id="test-book-ch001-0001",
            content="Connection before correction. Always establish emotional safety first.",
            book_slug="test-book",
            chapter_number=1,
            chapter_title="Introduction",
            start_position=81,
            end_position=150,
        ),
        Chunk(
            id="test-book-ch002-0000",
            content="Name it to tame it. Helping children label their emotions reduces intensity.",
            book_slug="test-book",
            chapter_number=2,
            chapter_title="Emotions",
            start_position=0,
            end_position=85,
        ),
    ]


@pytest.fixture
def sample_epub_content():
    """Sample content that mimics parsed ePub structure."""
    return {
        "title": "Test Parenting Book",
        "author": "Test Author",
        "chapters": [
            {
                "number": 1,
                "title": "Introduction",
                "content": (
                    "Children are good inside. When they act out, it's not because they're bad. "
                    "They're struggling with big emotions they don't know how to handle.\n\n"
                    "Connection before correction. Always establish emotional safety first. "
                    "When children feel connected, they're more receptive to guidance."
                ),
            },
            {
                "number": 2,
                "title": "Understanding Emotions",
                "content": (
                    "Name it to tame it. Helping children label their emotions reduces intensity. "
                    "When we put words to feelings, we activate the logical brain.\n\n"
                    "Emotion coaching is about being present with your child's feelings, "
                    "not trying to fix or dismiss them."
                ),
            },
        ],
    }


@pytest.fixture
def mock_embeddings():
    """Return mock embeddings for testing without loading the model."""
    # 384-dimensional vectors (matching all-MiniLM-L6-v2)
    import random

    def generate_embedding():
        return [random.random() for _ in range(384)]

    return generate_embedding
