"""Pattern-based clipboard text classification utilities.

The classifier in this module scores all known categories before choosing the
best match.  It is intentionally deterministic and defensive because clipboard
content can be empty, huge, or contain non-text/binary-looking data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable

MAX_CLASSIFICATION_CHARS = 100_000
BINARY_SAMPLE_CHARS = 4_096
BINARY_CONTROL_THRESHOLD = 0.08


class TextCategory(str, Enum):
    """Supported clipboard text categories."""

    URL = "URL"
    CODE = "CODE"
    MARKDOWN = "MARKDOWN"
    JSON = "JSON"
    XML = "XML"
    SQL = "SQL"
    TRACEBACK = "TRACEBACK"
    TODO = "TODO"
    CHAT = "CHAT"
    LOG = "LOG"
    NOTE = "NOTE"


@dataclass(frozen=True)
class ClassificationResult:
    """Structured classification response with confidence and scores."""

    category: TextCategory
    confidence: float
    scores: dict[TextCategory, float]


@dataclass(frozen=True)
class PatternRule:
    """A regex pattern and its contribution to a category score."""

    pattern: re.Pattern[str]
    weight: float = 1.0

    @classmethod
    def compile(cls, pattern: str, weight: float = 1.0) -> "PatternRule":
        return cls(re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL), weight)

    def score(self, text: str) -> float:
        if self.pattern.search(text):
            return self.weight
        return 0.0


def _rules(patterns: Iterable[tuple[str, float] | str]) -> tuple[PatternRule, ...]:
    compiled: list[PatternRule] = []
    for item in patterns:
        if isinstance(item, tuple):
            pattern, weight = item
        else:
            pattern, weight = item, 1.0
        compiled.append(PatternRule.compile(pattern, weight))
    return tuple(compiled)


class TextClassifier:
    """Classify clipboard text by weighted pattern scores.

    Every category is scored before the best category is selected.  If multiple
    categories have the same normalized score, the order in ``TIE_BREAK_ORDER``
    decides the winner so results never depend on dictionary iteration quirks.
    """

    TIE_BREAK_ORDER = (
        TextCategory.TRACEBACK,
        TextCategory.JSON,
        TextCategory.XML,
        TextCategory.SQL,
        TextCategory.URL,
        TextCategory.MARKDOWN,
        TextCategory.CODE,
        TextCategory.LOG,
        TextCategory.TODO,
        TextCategory.CHAT,
        TextCategory.NOTE,
    )

    PATTERNS: dict[TextCategory, tuple[PatternRule, ...]] = {
        TextCategory.URL: _rules(
            (
                (r"\bhttps?://[^\s<>()]+", 3.0),
                (r"\bwww\.[^\s<>()]+", 2.5),
                (r"\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.(?:com|org|net|edu|gov|io|ai|dev|app|co|uk|ca|de|fr|jp|au)(?:/[^\s<>()]*)?\b", 1.5),
                (r"[?&][a-z0-9_.~-]+=", 0.75),
            )
        ),
        TextCategory.CODE: _rules(
            (
                (r"^\s*(def|class|async\s+def|function)\s+[A-Za-z_][\w]*\s*\(", 2.5),
                (r"^\s*(import\s+[\w.]+|from\s+[\w.]+\s+import\s+|#include\s*[<\"])", 1.5),
                (r"\b(const|let|var)\s+[A-Za-z_$][\w$]*\s*=", 1.25),
                (r"\b(console\.log|print\s*\(|return\s+|=>)\b", 1.0),
                (r"[{};]\s*$", 0.75),
            )
        ),
        TextCategory.MARKDOWN: _rules(
            (
                (r"^\s{0,3}#{1,6}\s+\S", 2.0),
                (r"^\s{0,3}[-*+]\s+\S", 1.25),
                (r"^\s{0,3}>\s+\S", 1.0),
                (r"\[[^\]]+\]\([^\)]+\)", 1.25),
                (r"(```[\s\S]*?```|`[^`]+`|\*\*[^*]+\*\*)", 1.0),
            )
        ),
        TextCategory.JSON: _rules(
            (
                (r"^\s*[\[{][\s\S]*[\]}]\s*$", 2.0),
                (r"\"[A-Za-z_][\w -]*\"\s*:", 2.0),
                (r"\b(true|false|null)\b", 1.0),
                (r"^\s*\{\s*\"", 1.0),
            )
        ),
        TextCategory.XML: _rules(
            (
                (r"^\s*<\?xml\b", 2.0),
                (r"<([A-Za-z_][\w:.-]*)(?:\s+[^>]*)?>[\s\S]*</\1>", 2.0),
                (r"<[A-Za-z_][\w:.-]*(?:\s+[^>]*)?\s*/>", 1.25),
                (r"\s[A-Za-z_:][\w:.-]*=\"[^\"]*\"", 0.75),
            )
        ),
        TextCategory.SQL: _rules(
            (
                (r"\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE)\b", 2.5),
                (r"\bFROM\s+[A-Za-z_][\w.]*", 1.5),
                (r"\bWHERE\b", 1.0),
                (r"\b(JOIN|GROUP\s+BY|ORDER\s+BY|VALUES|SET)\b", 1.0),
                (r";\s*$", 0.5),
            )
        ),
        TextCategory.TRACEBACK: _rules(
            (
                (r"Traceback \(most recent call last\):", 3.0),
                (r"^\s*File \"[^\"]+\", line \d+", 2.0),
                (r"\b[A-Za-z_][\w]*(Error|Exception):\s+", 1.75),
                (r"\b(stack trace|caused by:)\b", 1.0),
            )
        ),
        TextCategory.TODO: _rules(
            (
                (r"\b(TODO|FIXME|HACK|XXX)\b", 2.0),
                (r"\b(to[- ]?do|task|action item|follow up)\b", 1.25),
                (r"\b(must|need to|should)\b", 0.75),
                (r"^\s*[-*]?\s*\[[ x]\]\s+", 1.0),
            )
        ),
        TextCategory.CHAT: _rules(
            (
                (r"\b(ChatGPT|Copilot|Claude|assistant|user:)\b", 1.75),
                (r"^\s*(User|Assistant|Human|AI):\s+", 2.0),
                (r"\b(question|answer):\s+", 1.0),
                (r"\b(prompt|conversation|chat transcript)\b", 1.0),
            )
        ),
        TextCategory.LOG: _rules(
            (
                (r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL)\b", 2.0),
                (r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", 1.5),
                (r"\[[A-Z]+\]", 1.0),
                (r"\b(pid|thread|request_id|status=|level=)\b", 1.0),
                (r"\b(exception|failed|failure)\b", 0.75),
            )
        ),
    }

    def classify_result(self, text: object) -> ClassificationResult:
        """Return a structured result for ``text``.

        Non-string, empty, whitespace-only, very large, and binary-like values
        are handled safely and fall back to ``NOTE`` when no text pattern should
        be trusted.
        """

        if not isinstance(text, str) or not text.strip() or self._looks_binary(text):
            return ClassificationResult(TextCategory.NOTE, 0.0, {})

        sample = text.strip()[:MAX_CLASSIFICATION_CHARS]
        raw_scores = {
            category: sum(rule.score(sample) for rule in patterns)
            for category, patterns in self.PATTERNS.items()
        }
        normalized_scores = {
            category: self._normalize(raw_scores[category], patterns)
            for category, patterns in self.PATTERNS.items()
        }
        best_category = self._best_category(normalized_scores)
        confidence = normalized_scores.get(best_category, 0.0)

        if confidence <= 0.0:
            return ClassificationResult(TextCategory.NOTE, 0.0, normalized_scores)
        return ClassificationResult(best_category, confidence, normalized_scores)

    def classify(self, text: object, confidence: bool = False) -> str | tuple[str, float]:
        """Classify text, optionally returning ``(category, confidence)``."""

        result = self.classify_result(text)
        if confidence:
            return result.category.value, result.confidence
        return result.category.value

    def get_all_categories(self) -> list[str]:
        """Return all supported category names in enum order."""

        return [category.value for category in TextCategory]

    @classmethod
    def _best_category(cls, scores: dict[TextCategory, float]) -> TextCategory:
        best = TextCategory.NOTE
        best_score = 0.0
        for category in cls.TIE_BREAK_ORDER:
            score = scores.get(category, 0.0)
            if score > best_score:
                best = category
                best_score = score
        return best

    @staticmethod
    def _normalize(raw_score: float, patterns: tuple[PatternRule, ...]) -> float:
        max_score = sum(rule.weight for rule in patterns) or 1.0
        return round(min(raw_score / max_score, 1.0), 4)

    @staticmethod
    def _looks_binary(text: str) -> bool:
        sample = text[:BINARY_SAMPLE_CHARS]
        if "\x00" in sample:
            return True
        if not sample:
            return False
        control_chars = sum(
            1 for char in sample if ord(char) < 32 and char not in "\t\n\r\f\v"
        )
        return control_chars / len(sample) > BINARY_CONTROL_THRESHOLD


classifier = TextClassifier()


def classify_text(text: object) -> str:
    """Backward-compatible wrapper returning only the category name."""

    return classifier.classify(text)
