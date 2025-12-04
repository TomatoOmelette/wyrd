"""SQLite metadata storage for books and chapters."""

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator


@dataclass
class BookRecord:
    """A book record from the database."""

    slug: str
    title: str
    author: str
    subject: str
    file_path: str | None
    added_at: datetime
    chunk_count: int = 0


@dataclass
class ChapterRecord:
    """A chapter record from the database."""

    id: int
    book_slug: str
    number: int
    title: str
    start_position: int
    end_position: int


class MetadataStore:
    """SQLite-based metadata storage."""

    def __init__(self, storage_path: str | Path | None = None):
        """
        Initialize the metadata store.

        Args:
            storage_path: Path to the database file. Defaults to WYRD_STORAGE_PATH/metadata.db
        """
        if storage_path is None:
            base_path = os.environ.get("WYRD_STORAGE_PATH", "./storage")
            storage_path = Path(base_path) / "metadata.db"
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
                CREATE TABLE IF NOT EXISTS books (
                    slug TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT,
                    subject TEXT NOT NULL DEFAULT 'general',
                    file_path TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    chunk_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS chapters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_slug TEXT NOT NULL REFERENCES books(slug) ON DELETE CASCADE,
                    number INTEGER NOT NULL,
                    title TEXT,
                    start_position INTEGER,
                    end_position INTEGER,
                    UNIQUE(book_slug, number)
                );

                CREATE INDEX IF NOT EXISTS idx_chapters_book ON chapters(book_slug);
                CREATE INDEX IF NOT EXISTS idx_books_subject ON books(subject);
                """
            )
            # Migration: add subject column if it doesn't exist
            try:
                conn.execute("ALTER TABLE books ADD COLUMN subject TEXT NOT NULL DEFAULT 'general'")
            except sqlite3.OperationalError:
                pass  # Column already exists

    def add_book(
        self,
        slug: str,
        title: str,
        author: str,
        subject: str = "general",
        file_path: str | None = None,
    ) -> BookRecord:
        """
        Add a book to the database.

        Args:
            slug: Unique identifier for the book
            title: Book title
            author: Book author
            subject: Subject/collection for the book (e.g., 'parenting', 'networking')
            file_path: Optional path to the source file

        Returns:
            The created BookRecord
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO books (slug, title, author, subject, file_path)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    title = excluded.title,
                    author = excluded.author,
                    subject = excluded.subject,
                    file_path = excluded.file_path
                """,
                (slug, title, author, subject, file_path),
            )

        return self.get_book(slug)  # type: ignore

    def add_chapters(
        self,
        book_slug: str,
        chapters: list[tuple[int, str, int, int]],
    ) -> None:
        """
        Add chapters for a book.

        Args:
            book_slug: The book identifier
            chapters: List of (number, title, start_position, end_position) tuples
        """
        with self._get_connection() as conn:
            # Clear existing chapters
            conn.execute("DELETE FROM chapters WHERE book_slug = ?", (book_slug,))

            # Insert new chapters
            conn.executemany(
                """
                INSERT INTO chapters (book_slug, number, title, start_position, end_position)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(book_slug, num, title, start, end) for num, title, start, end in chapters],
            )

    def update_chunk_count(self, slug: str, count: int) -> None:
        """Update the chunk count for a book."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE books SET chunk_count = ? WHERE slug = ?",
                (count, slug),
            )

    def get_book(self, slug: str) -> BookRecord | None:
        """Get a book by slug."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM books WHERE slug = ?", (slug,)
            ).fetchone()

            if row:
                return BookRecord(
                    slug=row["slug"],
                    title=row["title"],
                    author=row["author"],
                    subject=row["subject"],
                    file_path=row["file_path"],
                    added_at=datetime.fromisoformat(row["added_at"]),
                    chunk_count=row["chunk_count"],
                )
            return None

    def get_all_books(self, subject: str | None = None) -> list[BookRecord]:
        """Get all books, optionally filtered by subject."""
        with self._get_connection() as conn:
            if subject:
                rows = conn.execute(
                    "SELECT * FROM books WHERE subject = ? ORDER BY added_at DESC",
                    (subject,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM books ORDER BY added_at DESC"
                ).fetchall()

            return [
                BookRecord(
                    slug=row["slug"],
                    title=row["title"],
                    author=row["author"],
                    subject=row["subject"],
                    file_path=row["file_path"],
                    added_at=datetime.fromisoformat(row["added_at"]),
                    chunk_count=row["chunk_count"],
                )
                for row in rows
            ]

    def get_all_subjects(self) -> list[str]:
        """Get all unique subjects."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT subject FROM books ORDER BY subject"
            ).fetchall()
            return [row["subject"] for row in rows]

    def get_books_by_subject(self, subject: str) -> list[BookRecord]:
        """Get all books in a subject."""
        return self.get_all_books(subject=subject)

    def get_chapters(self, book_slug: str) -> list[ChapterRecord]:
        """Get all chapters for a book."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chapters WHERE book_slug = ? ORDER BY number",
                (book_slug,),
            ).fetchall()

            return [
                ChapterRecord(
                    id=row["id"],
                    book_slug=row["book_slug"],
                    number=row["number"],
                    title=row["title"],
                    start_position=row["start_position"],
                    end_position=row["end_position"],
                )
                for row in rows
            ]

    def delete_book(self, slug: str) -> bool:
        """
        Delete a book and its chapters.

        Args:
            slug: The book identifier

        Returns:
            True if the book was deleted, False if it didn't exist
        """
        with self._get_connection() as conn:
            # Chapters are deleted via CASCADE
            result = conn.execute("DELETE FROM books WHERE slug = ?", (slug,))
            return result.rowcount > 0

    def book_exists(self, slug: str) -> bool:
        """Check if a book exists."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM books WHERE slug = ?", (slug,)
            ).fetchone()
            return row is not None
