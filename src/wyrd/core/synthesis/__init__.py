"""Synthesis: summarization and formatting before returning to LLM."""

from wyrd.core.synthesis.llm_summarizer import (
    ChapterSummary,
    LLMSummarizer,
    format_chapter_summary,
)
from wyrd.core.synthesis.synthesizer import (
    SourceComparison,
    SourcePerspective,
    SynthesizedAdvice,
    Synthesizer,
    format_advice,
    format_comparison,
)

__all__ = [
    "ChapterSummary",
    "LLMSummarizer",
    "SourceComparison",
    "SourcePerspective",
    "SynthesizedAdvice",
    "Synthesizer",
    "format_advice",
    "format_chapter_summary",
    "format_comparison",
]
