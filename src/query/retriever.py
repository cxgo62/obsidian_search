from __future__ import annotations

from typing import Any

from app.config import AppSettings
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
