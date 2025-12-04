"""Book ingestion: parsing ePubs/PDFs into chunks and embeddings."""

from wyrd.core.ingestion.chunker import Chunk, chunk_chapter, chunk_text
from wyrd.core.ingestion.embedder import Embedder, SentenceTransformerEmbedder, get_embedder
from wyrd.core.ingestion.epub import BookContent, Chapter, parse_epub

__all__ = [
    "BookContent",
    "Chapter",
    "Chunk",
    "Embedder",
    "SentenceTransformerEmbedder",
    "chunk_chapter",
    "chunk_text",
    "get_embedder",
    "parse_epub",
]
