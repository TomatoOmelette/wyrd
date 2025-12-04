"""Text chunking for embedding."""

from dataclasses import dataclass


@dataclass
class Chunk:
    """A chunk of text ready for embedding."""

    id: str
    content: str
    book_slug: str
    chapter_number: int
    chapter_title: str
    start_position: int  # Position within the chapter
    end_position: int

    @property
    def metadata(self) -> dict:
        """Return metadata dict for storage."""
        return {
            "book_slug": self.book_slug,
            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,
            "start_position": self.start_position,
            "end_position": self.end_position,
        }


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[tuple[str, int, int]]:
    """
    Split text into overlapping chunks.

    Args:
        text: The text to chunk
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of (chunk_text, start_position, end_position) tuples
    """
    if not text.strip():
        return []

    chunks: list[tuple[str, int, int]] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = min(start + chunk_size, text_length)

        # Try to break at a sentence or paragraph boundary
        if end < text_length:
            # Look for paragraph break first
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + chunk_size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                for punct in [". ", "! ", "? ", ".\n", "!\n", "?\n"]:
                    sent_break = text.rfind(punct, start, end)
                    if sent_break > start + chunk_size // 2:
                        end = sent_break + len(punct)
                        break

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append((chunk_text, start, end))

        # Move start position, accounting for overlap
        start = end - chunk_overlap
        if start <= chunks[-1][1] if chunks else 0:
            # Avoid infinite loop if overlap is too large
            start = end

    return chunks


def chunk_chapter(
    chapter_content: str,
    book_slug: str,
    chapter_number: int,
    chapter_title: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[Chunk]:
    """
    Chunk a chapter's content into Chunk objects.

    Args:
        chapter_content: The chapter text
        book_slug: Identifier for the book
        chapter_number: Chapter number
        chapter_title: Chapter title
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        List of Chunk objects
    """
    raw_chunks = chunk_text(chapter_content, chunk_size, chunk_overlap)

    chunks = []
    for i, (content, start, end) in enumerate(raw_chunks):
        chunk_id = f"{book_slug}-ch{chapter_number:03d}-{i:04d}"
        chunks.append(
            Chunk(
                id=chunk_id,
                content=content,
                book_slug=book_slug,
                chapter_number=chapter_number,
                chapter_title=chapter_title,
                start_position=start,
                end_position=end,
            )
        )

    return chunks
