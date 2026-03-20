from __future__ import annotations

import json
import re
from typing import Any

from app.config import AppSettings
from query.query_expansion import expand_query
from query.ranker import dedup_hits, fuse_scores, group_by_note
from query.retriever import Retriever
from storage.sqlite_repo import SQLiteRepo

ANCHOR_STOPWORDS = {
    "api",
    "http",
    "https",
    "www",
    "com",
    "org",
    "net",
    "rest",
    "json",
    "xml",
    "管理",
    "系统",
    "模块",
    "接口",
    "服务",
    "功能",
    "方案",
    "流程",
    "问题",
    "方法",
    "数据",
    "设计",
    "开发",
}
ANCHOR_TOKEN_RE = re.compile(r"[0-9A-Za-z_]+|[\u4e00-\u9fff]{2,}")


class QueryService:
    def __init__(self, settings: AppSettings, sqlite_repo: SQLiteRepo, retriever: Retriever) -> None:
        self._settings = settings
        self._sqlite = sqlite_repo
        self._retriever = retriever

    def query_note(self, note_path: str, top_k: int | None = None, threshold: float | None = None) -> dict[str, Any]:
        note_blocks = self._sqlite.get_blocks_by_note(note_path)
        if not note_blocks:
            return {"note_path": note_path, "blocks": [], "note_summary": {"related_notes": []}}

        retrieval_cfg = self._settings.retrieval.model_copy()
        if top_k is not None:
            retrieval_cfg.top_k = top_k
        if threshold is not None:
            retrieval_cfg.threshold = threshold

        block_results = []
        all_hits: list[dict[str, Any]] = []
        for block in note_blocks:
            query_text = self._build_note_block_query_text(block)
            semantic, lexical = self._retriever.retrieve_for_text(
                text=query_text,
                top_k_ann=retrieval_cfg.top_k_ann,
                exclude_note=note_path,
            )
            candidate_ids = [h["block_uid"] for h in semantic] + [h["block_uid"] for h in lexical]
            boosts = self._retriever.graph_boost_map(note_path, candidate_ids)
            fused = fuse_scores(semantic, lexical, boosts, retrieval_cfg)
            fused = dedup_hits(fused)
            fused = self._apply_content_anchor_rerank(query_text, fused, retrieval_cfg)
            for hit in fused:
                all_hits.append(hit)
            block_results.append(
                {
                    "block_uid": block["block_uid"],
                    "heading_path": json.loads(block["heading_path"]),
                    "text": block["raw_text"],
                    "matches": [
                        {
                            "match_block_uid": h["block_uid"],
                            "match_note_path": h["note_path"],
                            "score": h["final_score"],
                            "explain": {
                                "semantic": h["semantic"],
                                "lexical": h["lexical"],
                                "lexical_effective": h.get("lexical_effective", h["lexical"]),
                                "semantic_lexical_synergy": h.get("semantic_lexical_synergy", 0.0),
                                "content_anchor": h.get("content_anchor", 0.0),
                                "graph_boost": h["graph_boost"],
                            },
                        }
                        for h in fused
                    ],
                }
            )
        summary = group_by_note(dedup_hits(all_hits))
        return {
            "note_path": note_path,
            "note_summary": {"related_notes": summary},
            "blocks": block_results,
        }

    def query_block(self, block_uid: str, top_k: int | None = None) -> dict[str, Any]:
        row = self._sqlite.get_block(block_uid)
        if not row:
            return {"block_uid": block_uid, "matches": []}
        text = self._build_note_block_query_text(row)
        semantic, lexical = self._retriever.retrieve_for_text(text, top_k_ann=top_k)
        boosts = self._retriever.graph_boost_map(row["note_path"], [h["block_uid"] for h in semantic] + [h["block_uid"] for h in lexical])
        hits = dedup_hits(fuse_scores(semantic, lexical, boosts, self._settings.retrieval))
        hits = self._apply_content_anchor_rerank(text, hits, self._settings.retrieval)
        return {"block_uid": block_uid, "matches": self._enrich_hits(hits)}

    def search(
        self,
        text: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        retrieval_cfg = self._settings.retrieval.model_copy()
        if top_k is not None:
            retrieval_cfg.top_k = top_k
            retrieval_cfg.top_k_ann = max(top_k, retrieval_cfg.top_k_ann)
        if threshold is not None:
            retrieval_cfg.threshold = threshold
        if retrieval_cfg.query_expansion.enabled:
            variants = expand_query(text, retrieval_cfg.query_expansion)
            semantic, lexical = self._retriever.retrieve_for_queries(
                [variant.text for variant in variants],
                top_k_ann=retrieval_cfg.top_k_ann,
            )
        else:
            semantic, lexical = self._retriever.retrieve_for_text(text, top_k_ann=retrieval_cfg.top_k_ann)
        boosts = {h["block_uid"]: 0.0 for h in semantic}
        hits = dedup_hits(fuse_scores(semantic, lexical, boosts, retrieval_cfg))
        hits = self._apply_content_anchor_rerank(text, hits, retrieval_cfg)
        if not hits and (semantic or lexical):
            relaxed_cfg = retrieval_cfg.model_copy()
            relaxed_cfg.threshold = 0.0
            hits = dedup_hits(fuse_scores(semantic, lexical, boosts, relaxed_cfg))
            hits = self._apply_content_anchor_rerank(text, hits, relaxed_cfg)
        return {"query": text, "matches": self._enrich_hits(hits)}

    def _enrich_hits(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for h in hits:
            row = self._sqlite.get_block(h["block_uid"])
            if row is None:
                continue
            enriched.append(
                {
                    **h,
                    "snippet": row["raw_text"][:220],
                    "block_text": row["raw_text"],
                    "heading_path": json.loads(row["heading_path"]),
                    "char_start": row["char_start"],
                    "char_end": row["char_end"],
                }
            )
        return enriched

    def _build_note_block_query_text(self, block: Any) -> str:
        clean_text = str(block["clean_text"]).strip()
        heading_raw = block["heading_path"] if "heading_path" in block.keys() else None
        heading_path = json.loads(heading_raw) if heading_raw else []
        heading = " > ".join(str(x).strip() for x in heading_path if str(x).strip())
        if not heading:
            return clean_text
        return f"{heading}\n{clean_text}"

    def _apply_content_anchor_rerank(self, query_text: str, hits: list[dict[str, Any]], retrieval_cfg: Any) -> list[dict[str, Any]]:
        if not hits:
            return []
        query_terms = self._extract_anchor_terms(query_text)
        if not query_terms:
            return hits
        reranked: list[dict[str, Any]] = []
        for h in hits:
            row = self._sqlite.get_block(h["block_uid"])
            if row is None:
                continue
            target_terms = self._extract_anchor_terms(str(row["clean_text"]))
            overlap = len(query_terms & target_terms) / max(1, len(query_terms))
            lexical = float(h.get("lexical", 0.0))
            graph_boost = float(h.get("graph_boost", 0.0))
            semantic = float(h.get("semantic", 0.0))

            # Keep semantic candidates and down-weight weakly anchored results
            # instead of hard-dropping them. This avoids false negatives on
            # paraphrases with low lexical overlap.
            extra_penalty = 0.0
            if lexical <= 0.05 and graph_boost <= 0.0 and overlap < retrieval_cfg.semantic_only_anchor_floor:
                extra_penalty += 0.20
            if lexical <= 0.10 and overlap < retrieval_cfg.min_content_anchor:
                extra_penalty += 0.10
            if semantic < 0.35 and lexical <= 0.05 and graph_boost <= 0.0:
                extra_penalty += 0.10

            penalty_strength = min(0.95, float(retrieval_cfg.anchor_penalty_strength) + extra_penalty)
            adjusted = float(h["final_score"]) * (1.0 - penalty_strength * (1.0 - overlap))
            if adjusted <= 0.0:
                continue
            nh = dict(h)
            nh["content_anchor"] = overlap
            nh["final_score"] = adjusted
            reranked.append(nh)
        reranked.sort(key=lambda x: x["final_score"], reverse=True)
        return reranked[: retrieval_cfg.top_k]

    def _extract_anchor_terms(self, text: str) -> set[str]:
        terms: set[str] = set()
        for token in ANCHOR_TOKEN_RE.findall(text.lower()):
            if token in ANCHOR_STOPWORDS:
                continue
            if token.isascii() and len(token) < 3:
                continue
            terms.add(token)
        return terms
