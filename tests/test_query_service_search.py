from __future__ import annotations

import json

from app.config import AppSettings
from query.service import QueryService


class _FakeRetriever:
    def __init__(self) -> None:
        self.for_queries_calls: list[list[str]] = []
        self.for_text_calls: list[str] = []

    def retrieve_for_queries(
        self,
        queries: list[str],
        top_k_ann: int | None = None,
        exclude_note: str | None = None,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        self.for_queries_calls.append(list(queries))
        return (
            [{"block_uid": "b1", "note_path": "n.md", "semantic_score": 0.9}],
            [{"block_uid": "b1", "note_path": "n.md", "lex_score": 0.8}],
        )

    def retrieve_for_text(
        self,
        text: str,
        top_k_ann: int | None = None,
        exclude_note: str | None = None,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        self.for_text_calls.append(text)
        return (
            [{"block_uid": "b1", "note_path": "n.md", "semantic_score": 0.9}],
            [{"block_uid": "b1", "note_path": "n.md", "lex_score": 0.8}],
        )


class _FakeSQLite:
    def __init__(self) -> None:
        self._row = {
            "block_uid": "b1",
            "note_path": "n.md",
            "raw_text": "oauth2 refresh token rotation",
            "clean_text": "oauth2 refresh token rotation",
            "heading_path": json.dumps(["Auth"]),
            "char_start": 0,
            "char_end": 28,
        }

    def get_block(self, block_uid: str) -> dict[str, object] | None:
        if block_uid != "b1":
            return None
        return self._row


def test_search_uses_query_expansion_variants_when_enabled() -> None:
    settings = AppSettings(
        retrieval={
            "top_k": 5,
            "top_k_ann": 5,
            "threshold": 0.0,
            "query_expansion": {"enabled": True, "max_variants": 4, "min_token_length": 2},
        }
    )
    retriever = _FakeRetriever()
    service = QueryService(settings, _FakeSQLite(), retriever)  # type: ignore[arg-type]

    result = service.search("how to design oauth2 refresh token rotation", top_k=5)

    assert result["matches"]
    assert retriever.for_queries_calls
    assert not retriever.for_text_calls
    assert retriever.for_queries_calls[0][0] == "how to design oauth2 refresh token rotation"
    assert len(retriever.for_queries_calls[0]) >= 2


def test_search_falls_back_to_single_query_when_expansion_disabled() -> None:
    settings = AppSettings(
        retrieval={
            "top_k": 5,
            "top_k_ann": 5,
            "threshold": 0.0,
            "query_expansion": {"enabled": False, "max_variants": 4, "min_token_length": 2},
        }
    )
    retriever = _FakeRetriever()
    service = QueryService(settings, _FakeSQLite(), retriever)  # type: ignore[arg-type]

    result = service.search("oauth2 refresh token rotation", top_k=5)

    assert result["matches"]
    assert retriever.for_text_calls == ["oauth2 refresh token rotation"]
    assert not retriever.for_queries_calls


def test_anchor_rerank_keeps_semantic_hits_with_low_anchor_overlap() -> None:
    settings = AppSettings(
        retrieval={
            "top_k": 5,
            "top_k_ann": 5,
            "threshold": 0.0,
            "min_content_anchor": 0.4,
            "semantic_only_anchor_floor": 0.4,
            "anchor_penalty_strength": 0.45,
            "query_expansion": {"enabled": False},
        }
    )
    retriever = _FakeRetriever()
    sqlite = _FakeSQLite()
    sqlite._row["clean_text"] = "session renewal hardening lifecycle"
    service = QueryService(settings, sqlite, retriever)  # type: ignore[arg-type]

    hits = [
        {
            "block_uid": "b1",
            "note_path": "n.md",
            "semantic": 0.93,
            "lexical": 0.0,
            "graph_boost": 0.0,
            "final_score": 0.9,
        }
    ]
    reranked = service._apply_content_anchor_rerank(
        "oauth2 refresh token rotation strategy",
        hits,
        settings.retrieval,
    )

    assert len(reranked) == 1
    assert 0.0 <= reranked[0]["content_anchor"] < settings.retrieval.semantic_only_anchor_floor
    assert 0.0 < reranked[0]["final_score"] < hits[0]["final_score"]
