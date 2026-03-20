from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from app.config import QueryExpansionConfig

_TOKEN_RE = re.compile(r"[0-9A-Za-z_]+|[\u4e00-\u9fff]{2,}")
_WHITESPACE_RE = re.compile(r"\s+")

_BASE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "best",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "please",
    "tell",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
    "would",
    "you",
    "your",
    "原理",
    "机制",
    "概念",
    "解释",
    "介绍",
    "如何",
    "怎么",
    "怎样",
}
_KEYWORD_EXTRA_STOPWORDS = {
    "actually",
    "basically",
    "easily",
    "just",
    "quickly",
    "really",
    "safely",
    "simply",
    "similarly",
    "truly",
}
_COMPACT_EXTRA_STOPWORDS = {
    "actually",
    "basically",
    "easily",
    "just",
    "quickly",
    "really",
    "similarly",
    "truly",
}


@dataclass(frozen=True, slots=True)
class QueryVariant:
    text: str
    source: str
    weight: float


def expand_query(query: str, cfg: QueryExpansionConfig) -> list[QueryVariant]:
    original = _normalize_text(query)
    variants = [QueryVariant(text=original, source="original", weight=1.0)]
    limit = max(1, cfg.max_variants)
    if not cfg.enabled:
        return variants[:limit]

    seen = {_dedupe_key(original)}
    keyword_text = _build_variant_text(query, cfg.min_token_length, _BASE_STOPWORDS | _KEYWORD_EXTRA_STOPWORDS)
    if keyword_text and _dedupe_key(keyword_text) not in seen:
        variants.append(QueryVariant(text=keyword_text, source="keyword", weight=0.85))
        seen.add(_dedupe_key(keyword_text))

    compact_text = _build_compact_variant(query, cfg.min_token_length)
    if compact_text and _dedupe_key(compact_text) not in seen:
        variants.append(QueryVariant(text=compact_text, source="compact", weight=0.7))
        seen.add(_dedupe_key(compact_text))

    return variants[:limit]


def _build_compact_variant(query: str, min_token_length: int) -> str:
    if not _looks_like_long_question(query):
        return ""
    return _build_variant_text(query, min_token_length, _BASE_STOPWORDS | _COMPACT_EXTRA_STOPWORDS)


def _looks_like_long_question(query: str) -> bool:
    stripped = query.strip()
    if "?" in stripped:
        return True
    tokens = _tokenize(stripped)
    if len(tokens) >= 7:
        return True
    if not tokens:
        return False
    first = tokens[0].lower()
    return first in {"how", "what", "why", "when", "where", "which", "who", "can", "do", "does", "should"}


def _build_variant_text(query: str, min_token_length: int, stopwords: set[str]) -> str:
    tokens = _tokenize(query)
    filtered: list[str] = []
    for token in tokens:
        normalized = token.lower()
        if normalized in stopwords:
            continue
        if len(normalized) < min_token_length:
            continue
        filtered.append(token)
    return _normalize_text(" ".join(_dedupe_tokens(filtered)))


def _dedupe_tokens(tokens: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _dedupe_key(text: str) -> str:
    return _normalize_text(text).lower()
