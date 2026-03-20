from __future__ import annotations

from app.config import QueryExpansionConfig
from query.query_expansion import expand_query


def test_expand_query_keeps_original_and_adds_keyword_variant() -> None:
    variants = expand_query("oauth2 refresh token rotation 原理", QueryExpansionConfig())

    texts = [item.text for item in variants]

    assert texts[0] == "oauth2 refresh token rotation 原理"
    assert any(text == "oauth2 refresh token rotation" for text in texts)


def test_expand_query_dedupes_variants_and_honors_max_variants() -> None:
    cfg = QueryExpansionConfig(max_variants=2)

    variants = expand_query("alpha alpha beta", cfg)

    texts = [item.text for item in variants]

    assert texts == ["alpha alpha beta", "alpha beta"]
    assert len(texts) == 2


def test_expand_query_returns_original_only_when_disabled() -> None:
    variants = expand_query("How do I rotate refresh tokens?", QueryExpansionConfig(enabled=False))

    assert [item.text for item in variants] == ["How do I rotate refresh tokens?"]


def test_expand_query_adds_compact_variant_for_long_questions() -> None:
    variants = expand_query("How do I rotate refresh tokens safely in production?", QueryExpansionConfig())

    compact = [item.text for item in variants if item.source == "compact"]

    assert compact == ["rotate refresh tokens safely production"]
