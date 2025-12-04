"""ePub parsing and text extraction."""

from dataclasses import dataclass
from pathlib import Path

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


@dataclass
class Chapter:
    """A chapter extracted from an ePub."""

    number: int
    title: str
    content: str
    start_position: int  # Character position in full text
    end_position: int


@dataclass
class BookContent:
    """Extracted content from an ePub file."""

    title: str
    author: str
    chapters: list[Chapter]
    full_text: str


def extract_text_from_html(html_content: bytes | str) -> str:
    """Extract plain text from HTML content."""
    if isinstance(html_content, bytes):
        html_content = html_content.decode("utf-8", errors="ignore")

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "nav"]):
        element.decompose()

    # Get text with reasonable spacing
    text = soup.get_text(separator="\n", strip=True)

    # Clean up excessive whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)

    return text


def extract_chapter_title(item: epub.EpubItem, soup: BeautifulSoup) -> str:
    """Try to extract a chapter title from the content."""
    # Try heading tags first
    for tag in ["h1", "h2", "h3"]:
        heading = soup.find(tag)
        if heading:
            title = heading.get_text(strip=True)
            if title and len(title) < 200:  # Sanity check
                return title

    # Fall back to item title if available
    if hasattr(item, "title") and item.title:
        return item.title

    # Fall back to filename
    if hasattr(item, "file_name"):
        return Path(item.file_name).stem.replace("_", " ").replace("-", " ").title()

    return "Untitled"


def parse_epub(file_path: str | Path) -> BookContent:
    """
    Parse an ePub file and extract its content.

    Args:
        file_path: Path to the ePub file

    Returns:
        BookContent with extracted title, author, chapters, and full text
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"ePub file not found: {file_path}")

    book = epub.read_epub(str(file_path), options={"ignore_ncx": True})

    # Extract metadata
    title = "Unknown Title"
    author = "Unknown Author"

    if book.get_metadata("DC", "title"):
        title = book.get_metadata("DC", "title")[0][0]

    if book.get_metadata("DC", "creator"):
        author = book.get_metadata("DC", "creator")[0][0]

    # Extract chapters from spine (reading order)
    chapters: list[Chapter] = []
    full_text_parts: list[str] = []
    current_position = 0
    chapter_number = 0

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            soup = BeautifulSoup(content, "html.parser")
            text = extract_text_from_html(content)

            if not text.strip():
                continue

            chapter_number += 1
            chapter_title = extract_chapter_title(item, soup)

            start_position = current_position
            end_position = current_position + len(text)

            chapters.append(
                Chapter(
                    number=chapter_number,
                    title=chapter_title,
                    content=text,
                    start_position=start_position,
                    end_position=end_position,
                )
            )

            full_text_parts.append(text)
            current_position = end_position + 1  # +1 for separator

    full_text = "\n".join(full_text_parts)

    return BookContent(
        title=title,
        author=author,
        chapters=chapters,
        full_text=full_text,
    )
