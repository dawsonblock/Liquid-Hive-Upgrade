"""Text Processing Tool for LIQUID-HIVE
====================================

Advanced text processing capabilities including analysis, transformation,
and natural language processing features.
"""

import re
import statistics
from collections import Counter
from typing import Any

from .base_tool import BaseTool, ToolParameter, ToolParameterType, ToolResult


class TextProcessingTool(BaseTool):
    """Advanced text processing and analysis tool."""

    @property
    def name(self) -> str:
        return "text_processing"

    @property
    def description(self) -> str:
        return "Perform advanced text processing including analysis, transformation, and NLP operations"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="operation",
                type=ToolParameterType.STRING,
                description="Text processing operation to perform",
                required=True,
                choices=[
                    "analyze",
                    "summarize",
                    "extract_entities",
                    "sentiment",
                    "clean",
                    "normalize",
                    "tokenize",
                    "ngrams",
                    "similarity",
                    "translate_case",
                    "extract_patterns",
                    "word_frequency",
                ],
            ),
            ToolParameter(
                name="text",
                type=ToolParameterType.STRING,
                description="Input text to process",
                required=True,
            ),
            ToolParameter(
                name="text2",
                type=ToolParameterType.STRING,
                description="Second text for comparison operations",
                required=False,
            ),
            ToolParameter(
                name="pattern",
                type=ToolParameterType.STRING,
                description="Pattern for extraction operations (regex)",
                required=False,
            ),
            ToolParameter(
                name="n",
                type=ToolParameterType.INTEGER,
                description="N value for n-grams or top-N results",
                required=False,
                default=3,
                min_value=1,
                max_value=10,
            ),
            ToolParameter(
                name="case_type",
                type=ToolParameterType.STRING,
                description="Case transformation type",
                required=False,
                default="lower",
                choices=["lower", "upper", "title", "sentence", "camel", "snake"],
            ),
        ]

    @property
    def category(self) -> str:
        return "text"

    @property
    def risk_level(self) -> str:
        return "low"

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute text processing operation."""
        operation = parameters["operation"]
        text = parameters["text"]
        text2 = parameters.get("text2")
        pattern = parameters.get("pattern")
        n = parameters.get("n", 3)
        case_type = parameters.get("case_type", "lower")

        try:
            if operation == "analyze":
                result = self._analyze_text(text)
            elif operation == "summarize":
                result = self._summarize_text(text)
            elif operation == "extract_entities":
                result = self._extract_entities(text)
            elif operation == "sentiment":
                result = self._analyze_sentiment(text)
            elif operation == "clean":
                result = self._clean_text(text)
            elif operation == "normalize":
                result = self._normalize_text(text)
            elif operation == "tokenize":
                result = self._tokenize_text(text)
            elif operation == "ngrams":
                result = self._extract_ngrams(text, n)
            elif operation == "similarity":
                if not text2:
                    return ToolResult(
                        success=False, error="text2 required for similarity operation"
                    )
                result = self._calculate_similarity(text, text2)
            elif operation == "translate_case":
                result = self._transform_case(text, case_type)
            elif operation == "extract_patterns":
                if not pattern:
                    return ToolResult(
                        success=False, error="pattern required for extract_patterns operation"
                    )
                result = self._extract_patterns(text, pattern)
            elif operation == "word_frequency":
                result = self._word_frequency(text, n)
            else:
                return ToolResult(success=False, error=f"Unknown operation: {operation}")

            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "operation": operation,
                    "input_length": len(text),
                    "input_words": len(text.split()),
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=f"Text processing failed: {e!s}")

    def _analyze_text(self, text: str) -> dict[str, Any]:
        """Comprehensive text analysis."""
        words = text.split()
        sentences = re.split(r"[.!?]+", text)
        paragraphs = text.split("\n\n")

        # Character analysis
        char_counts = Counter(text.lower())

        # Word analysis
        word_lengths = [len(word.strip('.,!?;:"()[]')) for word in words]

        analysis = {
            "basic_stats": {
                "characters": len(text),
                "characters_no_spaces": len(text.replace(" ", "")),
                "words": len(words),
                "sentences": len([s for s in sentences if s.strip()]),
                "paragraphs": len([p for p in paragraphs if p.strip()]),
                "lines": len(text.splitlines()),
            },
            "word_stats": {
                "avg_word_length": statistics.mean(word_lengths) if word_lengths else 0,
                "max_word_length": max(word_lengths) if word_lengths else 0,
                "min_word_length": min(word_lengths) if word_lengths else 0,
                "unique_words": len(set(word.lower().strip('.,!?;:"()[]') for word in words)),
            },
            "readability": {
                "avg_sentence_length": len(words) / len([s for s in sentences if s.strip()])
                if sentences
                else 0,
                "avg_paragraph_length": len(words) / len([p for p in paragraphs if p.strip()])
                if paragraphs
                else 0,
            },
            "character_frequency": dict(char_counts.most_common(10)),
            "complexity_score": self._calculate_complexity(text),
        }

        return analysis

    def _calculate_complexity(self, text: str) -> float:
        """Calculate text complexity score (0-1, higher = more complex)."""
        words = text.split()
        if not words:
            return 0

        # Factors contributing to complexity
        avg_word_length = sum(len(word) for word in words) / len(words)
        unique_ratio = len(set(words)) / len(words)
        punctuation_ratio = sum(
            1 for char in text if not char.isalnum() and not char.isspace()
        ) / len(text)

        # Simple complexity score
        complexity = (
            (avg_word_length - 4) / 10  # Word length factor
            + unique_ratio  # Vocabulary diversity
            + punctuation_ratio * 2  # Punctuation complexity
        ) / 3

        return max(0, min(1, complexity))

    def _summarize_text(self, text: str) -> dict[str, Any]:
        """Basic extractive summarization."""
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 3:
            return {
                "summary": text,
                "summary_sentences": sentences,
                "compression_ratio": 1.0,
                "method": "no_compression_needed",
            }

        # Simple scoring: sentence position + word frequency
        word_freq = Counter(word.lower() for sentence in sentences for word in sentence.split())

        sentence_scores = []
        for i, sentence in enumerate(sentences):
            words = sentence.split()
            score = sum(word_freq[word.lower()] for word in words)
            # Boost score for first and last sentences
            if i == 0 or i == len(sentences) - 1:
                score *= 1.2
            sentence_scores.append((score / len(words) if words else 0, sentence))

        # Select top 3 sentences
        top_sentences = sorted(sentence_scores, reverse=True)[:3]
        summary_text = ". ".join(sentence for _, sentence in top_sentences) + "."

        return {
            "summary": summary_text,
            "summary_sentences": [sentence for _, sentence in top_sentences],
            "compression_ratio": len(summary_text) / len(text),
            "method": "extractive_frequency_based",
        }

    def _extract_entities(self, text: str) -> dict[str, Any]:
        """Simple entity extraction using patterns."""
        entities = {
            "emails": re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text),
            "urls": re.findall(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                text,
            ),
            "phone_numbers": re.findall(
                r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", text
            ),
            "dates": re.findall(
                r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b", text
            ),
            "numbers": re.findall(r"\b\d+(?:\.\d+)?\b", text),
            "capitalized_words": re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", text),
        }

        return {
            "entities": entities,
            "entity_counts": {key: len(values) for key, values in entities.items()},
            "total_entities": sum(len(values) for values in entities.values()),
        }

    def _analyze_sentiment(self, text: str) -> dict[str, Any]:
        """Basic sentiment analysis using word patterns."""
        # Simple word lists (in production, use proper sentiment analysis library)
        positive_words = {
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
            "awesome",
            "love",
            "like",
            "enjoy",
            "happy",
            "pleased",
            "satisfied",
            "perfect",
            "best",
            "brilliant",
            "outstanding",
            "superb",
            "magnificent",
        }

        negative_words = {
            "bad",
            "terrible",
            "awful",
            "horrible",
            "disgusting",
            "hate",
            "dislike",
            "angry",
            "frustrated",
            "disappointed",
            "sad",
            "upset",
            "annoying",
            "worst",
            "failure",
            "useless",
            "broken",
            "wrong",
            "problem",
        }

        words = re.findall(r"\b\w+\b", text.lower())

        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)

        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            sentiment = "neutral"
            confidence = 0.5
        elif positive_count > negative_count:
            sentiment = "positive"
            confidence = positive_count / total_sentiment_words
        elif negative_count > positive_count:
            sentiment = "negative"
            confidence = negative_count / total_sentiment_words
        else:
            sentiment = "neutral"
            confidence = 0.5

        return {
            "sentiment": sentiment,
            "confidence": confidence,
            "positive_words_count": positive_count,
            "negative_words_count": negative_count,
            "total_sentiment_words": total_sentiment_words,
            "sentiment_ratio": (positive_count - negative_count) / len(words) if words else 0,
        }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", text)

        # Remove special characters but keep punctuation
        cleaned = re.sub(r"[^\w\s.,!?;:()-]", "", cleaned)

        # Normalize quotes
        cleaned = cleaned.replace('"', '"').replace('"', '"')
        cleaned = cleaned.replace(""", "'").replace(""", "'")

        return cleaned.strip()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for analysis."""
        # Convert to lowercase
        normalized = text.lower()

        # Remove punctuation
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    def _tokenize_text(self, text: str) -> list[str]:
        """Tokenize text into words."""
        return re.findall(r"\b\w+\b", text.lower())

    def _extract_ngrams(self, text: str, n: int) -> list[tuple[str, ...]]:
        """Extract n-grams from text."""
        tokens = self._tokenize_text(text)

        if len(tokens) < n:
            return []

        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i : i + n])
            ngrams.append(ngram)

        # Return most common n-grams
        ngram_counts = Counter(ngrams)
        return [
            {"ngram": " ".join(ngram), "tokens": ngram, "count": count}
            for ngram, count in ngram_counts.most_common(20)
        ]

    def _calculate_similarity(self, text1: str, text2: str) -> dict[str, Any]:
        """Calculate similarity between two texts."""
        tokens1 = set(self._tokenize_text(text1))
        tokens2 = set(self._tokenize_text(text2))

        # Jaccard similarity
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        jaccard = len(intersection) / len(union) if union else 0

        # Simple character-based similarity
        char_similarity = self._levenshtein_similarity(text1, text2)

        return {
            "jaccard_similarity": jaccard,
            "character_similarity": char_similarity,
            "common_words": list(intersection),
            "common_word_count": len(intersection),
            "unique_words_text1": len(tokens1 - tokens2),
            "unique_words_text2": len(tokens2 - tokens1),
        }

    def _levenshtein_similarity(self, text1: str, text2: str) -> float:
        """Calculate Levenshtein similarity (normalized)."""
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        # Simple Levenshtein distance calculation
        len1, len2 = len(text1), len(text2)
        if len1 > len2:
            text1, text2 = text2, text1
            len1, len2 = len2, len1

        current = list(range(len1 + 1))
        for i in range(1, len2 + 1):
            previous, current = current, [i] + [0] * len1
            for j in range(1, len1 + 1):
                add, delete, change = previous[j] + 1, current[j - 1] + 1, previous[j - 1]
                if text1[j - 1] != text2[i - 1]:
                    change += 1
                current[j] = min(add, delete, change)

        distance = current[len1]
        return 1 - distance / max(len1, len2)

    def _transform_case(self, text: str, case_type: str) -> str:
        """Transform text case."""
        if case_type == "lower":
            return text.lower()
        elif case_type == "upper":
            return text.upper()
        elif case_type == "title":
            return text.title()
        elif case_type == "sentence":
            return text.capitalize()
        elif case_type == "camel":
            words = re.sub(r"[^\w\s]", "", text).split()
            return words[0].lower() + "".join(word.capitalize() for word in words[1:])
        elif case_type == "snake":
            return re.sub(r"[^\w]", "_", text.lower())
        else:
            return text

    def _extract_patterns(self, text: str, pattern: str) -> list[dict[str, Any]]:
        """Extract patterns using regex."""
        matches = []
        for match in re.finditer(pattern, text):
            matches.append(
                {
                    "match": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "groups": match.groups() if match.groups() else [],
                }
            )

        return matches

    def _word_frequency(self, text: str, top_n: int) -> list[dict[str, Any]]:
        """Calculate word frequency."""
        words = self._tokenize_text(text)
        word_counts = Counter(words)

        return [
            {"word": word, "count": count, "frequency": count / len(words) if words else 0}
            for word, count in word_counts.most_common(top_n)
        ]
