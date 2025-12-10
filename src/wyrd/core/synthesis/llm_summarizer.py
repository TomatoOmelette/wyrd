"""LLM-based summarization for chapters and content."""

import os
from dataclasses import dataclass


@dataclass
class ChapterSummary:
    """Summary of a chapter."""

    book_slug: str
    chapter_number: int
    chapter_title: str
    summary: str
    key_points: list[str]
    chunk_count: int
    provider: str  # Which LLM provider was used


class LLMSummarizer:
    """LLM-based summarizer supporting multiple providers."""

    def __init__(self, provider: str | None = None, model: str | None = None):
        """
        Initialize the summarizer.

        Args:
            provider: LLM provider (ollama, openai, anthropic). Defaults to WYRD_SYNTHESIS_PROVIDER env var.
            model: Model name. Defaults vary by provider.
        """
        self.provider = provider or os.environ.get("WYRD_SYNTHESIS_PROVIDER", "none")
        self.model = model
        self._client = None

    def _get_default_model(self) -> str:
        """Get the default model for the current provider."""
        defaults = {
            "ollama": "llama3.2",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
        }
        return defaults.get(self.provider, "llama3.2")

    def _build_prompt(self, chapter_title: str, content: str) -> str:
        """Build the summarization prompt."""
        return f"""Summarize the following chapter from a book. Provide:
1. A concise summary (2-3 paragraphs)
2. 3-5 key points or takeaways

Chapter: {chapter_title}

Content:
{content}

Format your response as:
SUMMARY:
[Your summary here]

KEY POINTS:
- [Point 1]
- [Point 2]
- [Point 3]
"""

    def _parse_response(self, response: str) -> tuple[str, list[str]]:
        """Parse the LLM response into summary and key points."""
        summary = ""
        key_points = []

        lines = response.strip().split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if line.upper().startswith("SUMMARY:"):
                current_section = "summary"
                # Check if summary is on the same line
                rest = line[8:].strip()
                if rest:
                    summary = rest
            elif line.upper().startswith("KEY POINTS:"):
                current_section = "key_points"
            elif current_section == "summary" and line:
                if summary:
                    summary += " " + line
                else:
                    summary = line
            elif current_section == "key_points" and line:
                if line.startswith("- ") or line.startswith("* "):
                    key_points.append(line[2:])
                elif line[0].isdigit() and (". " in line[:4] or ") " in line[:4]):
                    # Handle numbered lists like "1. " or "1) "
                    key_points.append(line.split(" ", 1)[1] if " " in line else line)
                elif key_points:
                    # Continuation of previous point
                    key_points[-1] += " " + line
                else:
                    key_points.append(line)

        return summary, key_points

    def _summarize_ollama(self, chapter_title: str, content: str) -> tuple[str, list[str]]:
        """Summarize using Ollama."""
        try:
            import ollama
        except ImportError:
            raise ImportError("ollama package not installed. Run: pip install ollama")

        model = self.model or self._get_default_model()
        host = os.environ.get("WYRD_OLLAMA_HOST")

        client = ollama.Client(host=host) if host else ollama.Client()
        prompt = self._build_prompt(chapter_title, content)

        response = client.generate(model=model, prompt=prompt)
        return self._parse_response(response["response"])

    def _summarize_openai(self, chapter_title: str, content: str) -> tuple[str, list[str]]:
        """Summarize using OpenAI."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        model = self.model or self._get_default_model()
        client = openai.OpenAI()
        prompt = self._build_prompt(chapter_title, content)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_response(response.choices[0].message.content or "")

    def _summarize_anthropic(self, chapter_title: str, content: str) -> tuple[str, list[str]]:
        """Summarize using Anthropic."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        model = self.model or self._get_default_model()
        client = anthropic.Anthropic()
        prompt = self._build_prompt(chapter_title, content)

        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""
        return self._parse_response(text)

    def _summarize_rule_based(self, chapter_title: str, content: str) -> tuple[str, list[str]]:
        """Fallback rule-based summarization (extract first sentences)."""
        sentences = []
        current = []

        for char in content:
            current.append(char)
            if char in ".!?" and len(current) > 30:
                sentence = "".join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []

        # Take first few sentences as summary
        summary = " ".join(sentences[:5]) if sentences else content[:500]
        if len(summary) > 1000:
            summary = summary[:997] + "..."

        # Extract longer sentences as key points
        key_points = [s for s in sentences if 50 < len(s) < 200][:5]

        return summary, key_points

    def summarize_chapter(
        self,
        book_slug: str,
        chapter_number: int,
        chapter_title: str,
        chunks: list[dict],
    ) -> ChapterSummary:
        """
        Summarize a chapter from its chunks.

        Args:
            book_slug: The book identifier
            chapter_number: The chapter number
            chapter_title: The chapter title
            chunks: List of chunk dicts with 'content' key

        Returns:
            ChapterSummary with the summary and key points
        """
        # Combine all chunk content
        content = "\n\n".join(c["content"] for c in chunks if c.get("content"))

        # Truncate if too long for LLM context
        max_content_length = 15000  # Conservative limit
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n\n[Content truncated...]"

        # Route to appropriate provider
        if self.provider == "ollama":
            summary, key_points = self._summarize_ollama(chapter_title, content)
        elif self.provider == "openai":
            summary, key_points = self._summarize_openai(chapter_title, content)
        elif self.provider == "anthropic":
            summary, key_points = self._summarize_anthropic(chapter_title, content)
        else:
            # Fallback to rule-based
            summary, key_points = self._summarize_rule_based(chapter_title, content)
            self.provider = "rule-based"

        return ChapterSummary(
            book_slug=book_slug,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            summary=summary,
            key_points=key_points,
            chunk_count=len(chunks),
            provider=self.provider,
        )


def format_chapter_summary(summary: ChapterSummary) -> str:
    """Format a chapter summary for display."""
    parts = []

    parts.append(f"Chapter {summary.chapter_number}: {summary.chapter_title}")
    parts.append("=" * len(parts[0]))
    parts.append("")
    parts.append(summary.summary)
    parts.append("")

    if summary.key_points:
        parts.append("Key Points:")
        for point in summary.key_points:
            parts.append(f"  • {point}")
        parts.append("")

    parts.append(f"[Based on {summary.chunk_count} chunks, summarized by {summary.provider}]")

    return "\n".join(parts)
