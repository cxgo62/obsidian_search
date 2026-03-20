from __future__ import annotations

from typing import Any

from app.config import AppSettings
from query.ranker import merge_candidate_lists
from indexing.embedder import Embedder
from storage.milvus_repo import MilvusRepo
from storage.sqlite_repo import SQLiteRepo


class Retriever:
    def __init__(
        self,
        settings: AppSettings,
        sqlite_repo: SQLiteRepo,
        milvus_repo: MilvusRepo,
        embedder: Embedder,
    ) -> None:
        self._settings = settings
        self._sqlite = sqlite_repo
        self._milvus = milvus_repo
        self._embedder = embedder

    def retrieve_for_text(
        self,
        text: str,
        top_k_ann: int | None = None,
        exclude_note: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        top_k_ann = top_k_ann or self._settings.retrieval.top_k_ann
        vector = self._embedder.embed_texts([text])[0]
        semantic = self._milvus.search(vector, top_k_ann, exclude_note=exclude_note)
        lexical = self._sqlite.lexical_search(text, top_k_ann)
        return semantic, lexical

    def retrieve_for_queries(
        self,
        queries: list[str],
        top_k_ann: int | None = None,
        exclude_note: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        normalized = [q.strip() for q in queries if q and q.strip()]
        if not normalized:
            return [], []

        unique_queries = list(dict.fromkeys(normalized))
        if len(unique_queries) == 1:
            return self.retrieve_for_text(unique_queries[0], top_k_ann=top_k_ann, exclude_note=exclude_note)

        top_k_ann = top_k_ann or self._settings.retrieval.top_k_ann
        vectors = self._embedder.embed_texts(unique_queries)

        semantic_lists: list[list[dict[str, Any]]] = []
        lexical_lists: list[list[dict[str, Any]]] = []
        for idx, query in enumerate(unique_queries):
            semantic_lists.append(self._milvus.search(vectors[idx], top_k_ann, exclude_note=exclude_note))
            lexical_lists.append(self._sqlite.lexical_search(query, top_k_ann))

        semantic = self._merge_scored_hits(semantic_lists, score_key="semantic_score")
        lexical = self._merge_scored_hits(lexical_lists, score_key="lex_score")
        return semantic, lexical

    def graph_boost_map(self, src_note_path: str, candidate_block_uids: list[str]) -> dict[str, float]:
        src_links = self._sqlite.links_from_note(src_note_path)
        dst_notes = {row["dst_note_path"] for row in src_links}
        boosts: dict[str, float] = {}
        for uid in candidate_block_uids:
            row = self._sqlite.get_block(uid)
            if not row:
                continue
            note_path = row["note_path"]
            boosts[uid] = 1.0 if note_path in dst_notes else 0.0
        return boosts

    def _merge_scored_hits(self, hit_lists: list[list[dict[str, Any]]], score_key: str) -> list[dict[str, Any]]:
        if not hit_lists:
            return []
        ordered = merge_candidate_lists(hit_lists, key_fn=lambda row: row["block_uid"])
        best_by_uid: dict[str, dict[str, Any]] = {}
        for rows in hit_lists:
            for row in rows:
                uid = str(row["block_uid"])
                score = float(row.get(score_key, 0.0))
                cur = best_by_uid.get(uid)
                if cur is None or score > float(cur.get(score_key, 0.0)):
                    best_by_uid[uid] = dict(row)
        merged: list[dict[str, Any]] = []
        for row in ordered:
            uid = str(row["block_uid"])
            if uid in best_by_uid:
                merged.append(best_by_uid[uid])
        return merged
