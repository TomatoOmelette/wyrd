"""Topic extraction from text content."""

import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class ExtractedTopic:
    """A topic extracted from text."""

    id: str  # slug form
    display_name: str
    relevance: float  # 0-1 score


class TopicExtractor:
    """Extract topics from text using keyword analysis.

    This is a simple keyword-based extractor. For better results,
    consider using an LLM-based approach via the `extract_topics_llm` method.
    """

    # Common English stop words to ignore
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "need",
        "dare", "ought", "used", "that", "this", "these", "those", "which",
        "who", "whom", "whose", "what", "where", "when", "why", "how",
        "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "just", "also", "now", "then", "here",
        "there", "if", "because", "while", "although", "though", "after",
        "before", "until", "unless", "since", "during", "about", "into",
        "through", "between", "under", "above", "up", "down", "out", "off",
        "over", "again", "further", "once", "always", "never", "sometimes",
        "often", "usually", "really", "quite", "rather", "almost", "already",
        "still", "even", "back", "well", "much", "many", "any", "another",
        "like", "get", "got", "go", "going", "make", "made", "say", "said",
        "see", "seen", "come", "came", "take", "took", "know", "knew",
        "think", "thought", "want", "wanted", "give", "gave", "tell", "told",
        "find", "found", "feel", "felt", "try", "tried", "leave", "left",
        "put", "keep", "kept", "let", "begin", "began", "seem", "seemed",
        "help", "helped", "show", "showed", "hear", "heard", "play", "played",
        "run", "ran", "move", "moved", "live", "lived", "believe", "believed",
        "hold", "held", "bring", "brought", "happen", "happened", "write",
        "wrote", "provide", "provided", "sit", "sat", "stand", "stood",
        "lose", "lost", "pay", "paid", "meet", "met", "include", "included",
        "continue", "continued", "set", "learn", "learned", "change", "changed",
        "lead", "led", "understand", "understood", "watch", "watched",
        "follow", "followed", "stop", "stopped", "create", "created",
        "speak", "spoke", "read", "allow", "allowed", "add", "added",
        "spend", "spent", "grow", "grew", "open", "opened", "walk", "walked",
        "win", "won", "offer", "offered", "remember", "remembered",
        "love", "loved", "consider", "considered", "appear", "appeared",
        "buy", "bought", "wait", "waited", "serve", "served", "die", "died",
        "send", "sent", "expect", "expected", "build", "built", "stay", "stayed",
        "fall", "fell", "cut", "reach", "reached", "kill", "killed",
        "remain", "remained", "suggest", "suggested", "raise", "raised",
        "pass", "passed", "sell", "sold", "require", "required", "report",
        "reported", "decide", "decided", "pull", "pulled", "its", "it",
        "you", "your", "yours", "he", "him", "his", "she", "her", "hers",
        "we", "us", "our", "ours", "they", "them", "their", "theirs",
        "i", "me", "my", "mine", "myself", "yourself", "himself", "herself",
        "itself", "ourselves", "themselves", "one", "two", "three", "first",
        "second", "new", "old", "good", "bad", "great", "little", "big",
        "small", "long", "short", "high", "low", "young", "right", "left",
        "important", "different", "large", "next", "early", "late", "possible",
        "able", "sure", "free", "clear", "full", "kind", "nice", "whole",
        "special", "real", "best", "better", "hard", "last", "main", "others",
        "however", "therefore", "thus", "hence", "meanwhile", "instead",
        "don", "doesn", "didn", "won", "wouldn", "couldn", "shouldn",
        "isn", "aren", "wasn", "weren", "hasn", "haven", "hadn", "ll", "ve",
        "re", "s", "t", "d", "m", "chapter", "book", "page", "section",
    }

    # Minimum word length to consider
    MIN_WORD_LENGTH = 3

    # Minimum occurrences to be considered a topic
    MIN_OCCURRENCES = 2

    def __init__(
        self,
        min_word_length: int = 3,
        min_occurrences: int = 2,
        max_topics: int = 10,
        custom_stop_words: set[str] | None = None,
    ):
        """
        Initialize the topic extractor.

        Args:
            min_word_length: Minimum word length to consider
            min_occurrences: Minimum occurrences for a word to be a topic
            max_topics: Maximum number of topics to extract
            custom_stop_words: Additional stop words to ignore
        """
        self.min_word_length = min_word_length
        self.min_occurrences = min_occurrences
        self.max_topics = max_topics
        self.stop_words = self.STOP_WORDS | (custom_stop_words or set())

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        # Convert to lowercase
        text = text.lower()
        # Extract words (alphanumeric sequences)
        words = re.findall(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+)*\b", text)
        return words

    def _slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug."""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text.strip("-")

    def _extract_ngrams(self, words: list[str], n: int = 2) -> list[str]:
        """Extract n-grams from word list."""
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i : i + n])
            # Skip if any word is a stop word
            if not any(w in self.stop_words for w in words[i : i + n]):
                ngrams.append(ngram)
        return ngrams

    def extract(self, text: str, subject: str = "general") -> list[ExtractedTopic]:
        """
        Extract topics from text.

        Args:
            text: The text to extract topics from
            subject: Subject context (used for filtering)

        Returns:
            List of extracted topics, ordered by relevance
        """
        words = self._tokenize(text)

        # Filter words
        filtered_words = [
            w for w in words
            if len(w) >= self.min_word_length
            and w not in self.stop_words
            and not w.isdigit()
        ]

        # Count single words
        word_counts = Counter(filtered_words)

        # Also extract bigrams for compound topics
        bigrams = self._extract_ngrams(words, 2)
        bigram_counts = Counter(bigrams)

        # Combine and score
        topics: dict[str, float] = {}

        # Add single-word topics
        total_words = len(filtered_words) or 1
        for word, count in word_counts.items():
            if count >= self.min_occurrences:
                # Relevance based on frequency, capped at 1.0
                relevance = min(count / (total_words * 0.1), 1.0)
                topics[word] = relevance

        # Add bigram topics (weighted higher)
        for bigram, count in bigram_counts.items():
            if count >= self.min_occurrences:
                relevance = min(count / (total_words * 0.05), 1.0)
                topics[bigram] = relevance

        # Sort by relevance and take top N
        sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)
        top_topics = sorted_topics[: self.max_topics]

        return [
            ExtractedTopic(
                id=self._slugify(name),
                display_name=name.title(),
                relevance=relevance,
            )
            for name, relevance in top_topics
        ]

    def extract_from_chunks(
        self,
        chunks: list[tuple[str, str]],  # (chunk_id, content)
        subject: str = "general",
    ) -> dict[str, list[tuple[str, float]]]:
        """
        Extract topics from multiple chunks.

        Args:
            chunks: List of (chunk_id, content) tuples
            subject: Subject context

        Returns:
            Dict mapping topic_id to list of (chunk_id, relevance) tuples
        """
        topic_chunks: dict[str, list[tuple[str, float]]] = {}

        for chunk_id, content in chunks:
            topics = self.extract(content, subject)

            for topic in topics:
                if topic.id not in topic_chunks:
                    topic_chunks[topic.id] = []
                topic_chunks[topic.id].append((chunk_id, topic.relevance))

        return topic_chunks


# Convenience function
def extract_topics(
    text: str,
    max_topics: int = 10,
    min_occurrences: int = 2,
) -> list[ExtractedTopic]:
    """
    Extract topics from text.

    Args:
        text: The text to extract topics from
        max_topics: Maximum number of topics to return
        min_occurrences: Minimum occurrences for a word to be a topic

    Returns:
        List of extracted topics
    """
    extractor = TopicExtractor(
        max_topics=max_topics,
        min_occurrences=min_occurrences,
    )
    return extractor.extract(text)
