"""YAML data models for human-curated content."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SourceCitation:
    """Citation to a specific location in a book."""

    chapter: str
    location: int | None = None
    quote: str = ""


@dataclass
class CuratedPrinciple:
    """A principle extracted and curated from a book."""

    id: str
    title: str
    summary: str
    topics: list[str]
    source: SourceCitation
    concepts: list[str] = field(default_factory=list)


@dataclass
class CuratedStrategy:
    """An actionable strategy extracted and curated from a book."""

    id: str
    title: str
    summary: str
    topics: list[str]
    source: SourceCitation
    steps: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)


@dataclass
class BookPhilosophy:
    """The core philosophy of a book."""

    core_belief: str
    key_ideas: list[str]
    source: SourceCitation


@dataclass
class CuratedBook:
    """Curated content from a book."""

    slug: str
    title: str
    author: str
    short_name: str
    philosophy: BookPhilosophy | None = None
    principles: list[CuratedPrinciple] = field(default_factory=list)
    strategies: list[CuratedStrategy] = field(default_factory=list)


def _parse_source(data: dict[str, Any]) -> SourceCitation:
    """Parse a source citation from dict."""
    return SourceCitation(
        chapter=data.get("chapter", ""),
        location=data.get("location"),
        quote=data.get("quote", ""),
    )


def _parse_philosophy(data: dict[str, Any]) -> BookPhilosophy:
    """Parse philosophy from dict."""
    return BookPhilosophy(
        core_belief=data.get("core_belief", ""),
        key_ideas=data.get("key_ideas", []),
        source=_parse_source(data.get("source", {})),
    )


def _parse_principle(data: dict[str, Any]) -> CuratedPrinciple:
    """Parse a principle from dict."""
    return CuratedPrinciple(
        id=data.get("id", ""),
        title=data.get("title", ""),
        summary=data.get("summary", ""),
        topics=data.get("topics", []),
        source=_parse_source(data.get("source", {})),
        concepts=data.get("concepts", []),
    )


def _parse_strategy(data: dict[str, Any]) -> CuratedStrategy:
    """Parse a strategy from dict."""
    return CuratedStrategy(
        id=data.get("id", ""),
        title=data.get("title", ""),
        summary=data.get("summary", ""),
        topics=data.get("topics", []),
        source=_parse_source(data.get("source", {})),
        steps=data.get("steps", []),
        concepts=data.get("concepts", []),
    )


def load_curated_book(book_dir: Path) -> CuratedBook:
    """
    Load curated content from a book directory.

    Expected structure:
        book_dir/
            metadata.yaml      # Required: slug, title, author, short_name
            philosophy.yaml    # Optional: core philosophy
            principles.yaml    # Optional: key principles
            strategies.yaml    # Optional: actionable strategies

    Args:
        book_dir: Path to the book's curation directory

    Returns:
        CuratedBook with all available content
    """
    # Load required metadata
    metadata_path = book_dir / "metadata.yaml"
    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata.yaml not found in {book_dir}")

    with open(metadata_path) as f:
        metadata = yaml.safe_load(f) or {}

    curated = CuratedBook(
        slug=metadata.get("slug", book_dir.name),
        title=metadata.get("title", ""),
        author=metadata.get("author", ""),
        short_name=metadata.get("short_name", metadata.get("title", "")),
    )

    # Load optional philosophy
    philosophy_path = book_dir / "philosophy.yaml"
    if philosophy_path.exists():
        with open(philosophy_path) as f:
            data = yaml.safe_load(f) or {}
        if data:
            curated.philosophy = _parse_philosophy(data)

    # Load optional principles
    principles_path = book_dir / "principles.yaml"
    if principles_path.exists():
        with open(principles_path) as f:
            data = yaml.safe_load(f) or {}
        principles_list = data.get("principles", [])
        curated.principles = [_parse_principle(p) for p in principles_list]

    # Load optional strategies
    strategies_path = book_dir / "strategies.yaml"
    if strategies_path.exists():
        with open(strategies_path) as f:
            data = yaml.safe_load(f) or {}
        strategies_list = data.get("strategies", [])
        curated.strategies = [_parse_strategy(s) for s in strategies_list]

    return curated


def save_curated_book(book: CuratedBook, book_dir: Path) -> None:
    """
    Save curated content to a book directory.

    Args:
        book: The curated book content
        book_dir: Path to save the content
    """
    book_dir.mkdir(parents=True, exist_ok=True)

    # Save metadata
    metadata = {
        "slug": book.slug,
        "title": book.title,
        "author": book.author,
        "short_name": book.short_name,
    }
    with open(book_dir / "metadata.yaml", "w") as f:
        yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)

    # Save philosophy if present
    if book.philosophy:
        philosophy_data = {
            "core_belief": book.philosophy.core_belief,
            "key_ideas": book.philosophy.key_ideas,
            "source": {
                "chapter": book.philosophy.source.chapter,
                "location": book.philosophy.source.location,
                "quote": book.philosophy.source.quote,
            },
        }
        with open(book_dir / "philosophy.yaml", "w") as f:
            yaml.dump(philosophy_data, f, default_flow_style=False, allow_unicode=True)

    # Save principles if present
    if book.principles:
        principles_data = {
            "principles": [
                {
                    "id": p.id,
                    "title": p.title,
                    "summary": p.summary,
                    "topics": p.topics,
                    "concepts": p.concepts,
                    "source": {
                        "chapter": p.source.chapter,
                        "location": p.source.location,
                        "quote": p.source.quote,
                    },
                }
                for p in book.principles
            ]
        }
        with open(book_dir / "principles.yaml", "w") as f:
            yaml.dump(principles_data, f, default_flow_style=False, allow_unicode=True)

    # Save strategies if present
    if book.strategies:
        strategies_data = {
            "strategies": [
                {
                    "id": s.id,
                    "title": s.title,
                    "summary": s.summary,
                    "topics": s.topics,
                    "steps": s.steps,
                    "concepts": s.concepts,
                    "source": {
                        "chapter": s.source.chapter,
                        "location": s.source.location,
                        "quote": s.source.quote,
                    },
                }
                for s in book.strategies
            ]
        }
        with open(book_dir / "strategies.yaml", "w") as f:
            yaml.dump(strategies_data, f, default_flow_style=False, allow_unicode=True)


def generate_curation_template(book_slug: str, book_dir: Path) -> None:
    """
    Generate empty curation template files for a book.

    Args:
        book_slug: The book's slug identifier
        book_dir: Directory to create templates in
    """
    book_dir.mkdir(parents=True, exist_ok=True)

    # metadata.yaml template
    metadata_template = f"""\
# Book Metadata
slug: {book_slug}
title: ""  # Full book title
author: ""  # Author name(s)
short_name: ""  # Short name for citations
"""
    with open(book_dir / "metadata.yaml", "w") as f:
        f.write(metadata_template)

    # philosophy.yaml template
    philosophy_template = """\
# Core Philosophy
# Capture the book's fundamental worldview and key ideas

core_belief: ""  # The central belief or thesis

key_ideas:
  - ""  # Key idea 1
  - ""  # Key idea 2

source:
  chapter: ""
  location: null  # Kindle location or page number
  quote: ""
"""
    with open(book_dir / "philosophy.yaml", "w") as f:
        f.write(philosophy_template)

    # principles.yaml template
    principles_template = """\
# Key Principles
# Important concepts and mental models from the book

principles:
  - id: ""  # Unique identifier (e.g., slug-principle-001)
    title: ""
    summary: >
      Multi-line summary of the principle.
    topics:
      - ""  # Related topic from registry
    concepts:
      - ""  # Related concept for knowledge graph
    source:
      chapter: ""
      location: null
      quote: ""
"""
    with open(book_dir / "principles.yaml", "w") as f:
        f.write(principles_template)

    # strategies.yaml template
    strategies_template = """\
# Actionable Strategies
# Specific techniques and approaches from the book

strategies:
  - id: ""  # Unique identifier (e.g., slug-strategy-001)
    title: ""
    summary: >
      Brief description of the strategy.
    steps:
      - ""  # Step 1
      - ""  # Step 2
    topics:
      - ""  # Related topic
    concepts:
      - ""  # Related concept
    source:
      chapter: ""
      location: null
      quote: ""
"""
    with open(book_dir / "strategies.yaml", "w") as f:
        f.write(strategies_template)
