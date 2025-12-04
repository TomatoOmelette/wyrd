"""Topic registry for managing topics across books."""

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class Topic:
    """A topic in the registry."""

    id: str
    display_name: str
    description: str
    subject: str  # Which subject this topic belongs to
    related_topics: list[str]
    book_count: int = 0
    chunk_count: int = 0


@dataclass
class TopicOccurrence:
    """A topic occurrence in a specific chunk."""

    topic_id: str
    chunk_id: str
    book_slug: str
    relevance: float  # 0-1 score of how relevant this topic is to the chunk


class TopicRegistry:
    """SQLite-based topic registry."""

    def __init__(self, storage_path: str | Path | None = None):
        """
        Initialize the topic registry.

        Args:
            storage_path: Path to the database file. Defaults to WYRD_STORAGE_PATH/topics.db
        """
        if storage_path is None:
            base_path = os.environ.get("WYRD_STORAGE_PATH", "./storage")
            storage_path = Path(base_path) / "topics.db"
        else:
            storage_path = Path(storage_path)

        storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = storage_path
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS topics (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    subject TEXT NOT NULL DEFAULT 'general',
                    related_topics TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS topic_occurrences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                    chunk_id TEXT NOT NULL,
                    book_slug TEXT NOT NULL,
                    relevance REAL DEFAULT 1.0,
                    UNIQUE(topic_id, chunk_id)
                );

                CREATE INDEX IF NOT EXISTS idx_occurrences_topic ON topic_occurrences(topic_id);
                CREATE INDEX IF NOT EXISTS idx_occurrences_book ON topic_occurrences(book_slug);
                CREATE INDEX IF NOT EXISTS idx_occurrences_chunk ON topic_occurrences(chunk_id);
                CREATE INDEX IF NOT EXISTS idx_topics_subject ON topics(subject);
                """
            )

    def add_topic(
        self,
        topic_id: str,
        display_name: str,
        description: str = "",
        subject: str = "general",
        related_topics: list[str] | None = None,
    ) -> Topic:
        """
        Add or update a topic.

        Args:
            topic_id: Unique identifier (slug form)
            display_name: Human-readable name
            description: Optional description
            subject: Subject this topic belongs to
            related_topics: List of related topic IDs

        Returns:
            The created/updated Topic
        """
        related_str = ",".join(related_topics or [])

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO topics (id, display_name, description, subject, related_topics)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    display_name = excluded.display_name,
                    description = COALESCE(NULLIF(excluded.description, ''), topics.description),
                    subject = excluded.subject,
                    related_topics = excluded.related_topics
                """,
                (topic_id, display_name, description, subject, related_str),
            )

        return self.get_topic(topic_id)  # type: ignore

    def add_occurrence(
        self,
        topic_id: str,
        chunk_id: str,
        book_slug: str,
        relevance: float = 1.0,
    ) -> None:
        """
        Record that a topic appears in a chunk.

        Args:
            topic_id: The topic ID
            chunk_id: The chunk ID
            book_slug: The book slug
            relevance: How relevant this topic is (0-1)
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO topic_occurrences (topic_id, chunk_id, book_slug, relevance)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(topic_id, chunk_id) DO UPDATE SET
                    relevance = MAX(topic_occurrences.relevance, excluded.relevance)
                """,
                (topic_id, chunk_id, book_slug, relevance),
            )

    def get_topic(self, topic_id: str) -> Topic | None:
        """Get a topic by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM topics WHERE id = ?", (topic_id,)
            ).fetchone()

            if not row:
                return None

            # Get counts
            counts = conn.execute(
                """
                SELECT
                    COUNT(DISTINCT book_slug) as book_count,
                    COUNT(*) as chunk_count
                FROM topic_occurrences
                WHERE topic_id = ?
                """,
                (topic_id,),
            ).fetchone()

            related = row["related_topics"].split(",") if row["related_topics"] else []

            return Topic(
                id=row["id"],
                display_name=row["display_name"],
                description=row["description"],
                subject=row["subject"],
                related_topics=[r for r in related if r],
                book_count=counts["book_count"],
                chunk_count=counts["chunk_count"],
            )

    def get_all_topics(self, subject: str | None = None) -> list[Topic]:
        """Get all topics, optionally filtered by subject."""
        with self._get_connection() as conn:
            if subject:
                rows = conn.execute(
                    "SELECT * FROM topics WHERE subject = ? ORDER BY display_name",
                    (subject,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM topics ORDER BY display_name"
                ).fetchall()

            topics = []
            for row in rows:
                counts = conn.execute(
                    """
                    SELECT
                        COUNT(DISTINCT book_slug) as book_count,
                        COUNT(*) as chunk_count
                    FROM topic_occurrences
                    WHERE topic_id = ?
                    """,
                    (row["id"],),
                ).fetchone()

                related = row["related_topics"].split(",") if row["related_topics"] else []

                topics.append(
                    Topic(
                        id=row["id"],
                        display_name=row["display_name"],
                        description=row["description"],
                        subject=row["subject"],
                        related_topics=[r for r in related if r],
                        book_count=counts["book_count"],
                        chunk_count=counts["chunk_count"],
                    )
                )

            return topics

    def get_topics_for_book(self, book_slug: str) -> list[Topic]:
        """Get all topics that appear in a book."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT t.*
                FROM topics t
                JOIN topic_occurrences o ON t.id = o.topic_id
                WHERE o.book_slug = ?
                ORDER BY t.display_name
                """,
                (book_slug,),
            ).fetchall()

            topics = []
            for row in rows:
                counts = conn.execute(
                    """
                    SELECT
                        COUNT(DISTINCT book_slug) as book_count,
                        COUNT(*) as chunk_count
                    FROM topic_occurrences
                    WHERE topic_id = ?
                    """,
                    (row["id"],),
                ).fetchone()

                related = row["related_topics"].split(",") if row["related_topics"] else []

                topics.append(
                    Topic(
                        id=row["id"],
                        display_name=row["display_name"],
                        description=row["description"],
                        subject=row["subject"],
                        related_topics=[r for r in related if r],
                        book_count=counts["book_count"],
                        chunk_count=counts["chunk_count"],
                    )
                )

            return topics

    def get_chunks_for_topic(self, topic_id: str, book_slug: str | None = None) -> list[str]:
        """Get all chunk IDs for a topic, optionally filtered by book."""
        with self._get_connection() as conn:
            if book_slug:
                rows = conn.execute(
                    """
                    SELECT chunk_id FROM topic_occurrences
                    WHERE topic_id = ? AND book_slug = ?
                    ORDER BY relevance DESC
                    """,
                    (topic_id, book_slug),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT chunk_id FROM topic_occurrences
                    WHERE topic_id = ?
                    ORDER BY relevance DESC
                    """,
                    (topic_id,),
                ).fetchall()

            return [row["chunk_id"] for row in rows]

    def get_books_for_topic(self, topic_id: str) -> list[str]:
        """Get all book slugs that contain a topic."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT book_slug FROM topic_occurrences
                WHERE topic_id = ?
                """,
                (topic_id,),
            ).fetchall()

            return [row["book_slug"] for row in rows]

    def delete_by_book(self, book_slug: str) -> int:
        """
        Delete all topic occurrences for a book.

        Args:
            book_slug: The book identifier

        Returns:
            Number of occurrences deleted
        """
        with self._get_connection() as conn:
            result = conn.execute(
                "DELETE FROM topic_occurrences WHERE book_slug = ?",
                (book_slug,),
            )
            return result.rowcount

    def search_topics(self, query: str) -> list[Topic]:
        """
        Search topics by name or description.

        Args:
            query: Search term

        Returns:
            Matching topics
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM topics
                WHERE display_name LIKE ? OR description LIKE ? OR id LIKE ?
                ORDER BY display_name
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            ).fetchall()

            topics = []
            for row in rows:
                counts = conn.execute(
                    """
                    SELECT
                        COUNT(DISTINCT book_slug) as book_count,
                        COUNT(*) as chunk_count
                    FROM topic_occurrences
                    WHERE topic_id = ?
                    """,
                    (row["id"],),
                ).fetchone()

                related = row["related_topics"].split(",") if row["related_topics"] else []

                topics.append(
                    Topic(
                        id=row["id"],
                        display_name=row["display_name"],
                        description=row["description"],
                        subject=row["subject"],
                        related_topics=[r for r in related if r],
                        book_count=counts["book_count"],
                        chunk_count=counts["chunk_count"],
                    )
                )

            return topics
