"""Synthesis: summarization and formatting before returning to LLM."""

from wyrd.core.synthesis.synthesizer import (
    SourceComparison,
    SourcePerspective,
    SynthesizedAdvice,
    Synthesizer,
    format_advice,
    format_comparison,
)

__all__ = [
    "SourceComparison",
    "SourcePerspective",
    "SynthesizedAdvice",
    "Synthesizer",
    "format_advice",
    "format_comparison",
]
