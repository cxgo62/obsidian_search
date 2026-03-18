from __future__ import annotations

from collections import defaultdict
import math
from typing import Any

from app.config import RetrievalConfig


def fuse_scores(
    semantic_hits: list[dict[str, Any]],
    lexical_hits: list[dict[str, Any]],
    graph_boosts: dict[str, float],
    retrieval_cfg: RetrievalConfig,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in semantic_hits:
        merged[item["block_uid"]] = {
            "block_uid": item["block_uid"],
            "note_path": item.get("note_path"),
            "semantic": float(item.get("semantic_score", 0.0)),
            "lexical": 0.0,
            "graph_boost": graph_boosts.get(item["block_uid"], 0.0),
        }
    for item in lexical_hits:
        row = merged.setdefault(
            item["block_uid"],
            {
                "block_uid": item["block_uid"],
                "note_path": item.get("note_path"),
                "semantic": 0.0,
                "lexical": 0.0,
                "graph_boost": graph_boosts.get(item["block_uid"], 0.0),
            },
        )
        row["lexical"] = max(row["lexical"], float(item.get("lex_score", 0.0)))
    w = retrieval_cfg.weights
    out = []
    for row in merged.values():
        sem = _clamp01(row["semantic"])
        lex = _clamp01(row["lexical"])
        lexical_gate = retrieval_cfg.min_lexical_gate + (1.0 - retrieval_cfg.min_lexical_gate) * sem
        lexical_effective = lex * lexical_gate
        synergy = math.sqrt(max(0.0, sem * lex))
        row["semantic"] = sem
        row["lexical"] = lex
        row["lexical_effective"] = lexical_effective
        row["semantic_lexical_synergy"] = synergy
        row["final_score"] = w.sem * sem + w.lex * lexical_effective + w.graph * row["graph_boost"] + w.synergy * synergy
        if row["final_score"] >= retrieval_cfg.threshold:
            out.append(row)
    out.sort(key=lambda x: x["final_score"], reverse=True)
    return _apply_note_diversity(
        out,
        top_k=retrieval_cfg.top_k,
        max_hits_per_note=retrieval_cfg.max_hits_per_note,
        note_diversity_penalty=retrieval_cfg.note_diversity_penalty,
    )


def dedup_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for h in hits:
        key = (h["note_path"], h["block_uid"])
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def group_by_note(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for h in hits:
        bucket[h["note_path"]].append(h)
    out = []
    for note_path, rows in bucket.items():
        rows.sort(key=lambda x: x["final_score"], reverse=True)
        out.append(
            {
                "note_path": note_path,
                "score": rows[0]["final_score"],
                "top_blocks": rows[:3],
            }
        )
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


def _apply_note_diversity(
    hits: list[dict[str, Any]],
    top_k: int,
    max_hits_per_note: int,
    note_diversity_penalty: float,
) -> list[dict[str, Any]]:
    if not hits or top_k <= 0:
        return []
    if max_hits_per_note <= 0 and note_diversity_penalty <= 0:
        return hits[:top_k]

    selected: list[dict[str, Any]] = []
    note_counts: dict[str, int] = defaultdict(int)
    remaining = list(hits)
    while remaining and len(selected) < top_k:
        best_idx = -1
        best_adjusted_score = float("-inf")
        for idx, hit in enumerate(remaining):
            note_path = str(hit.get("note_path") or "")
            seen = note_counts[note_path]
            if max_hits_per_note > 0 and seen >= max_hits_per_note:
                continue
            adjusted = float(hit["final_score"]) - note_diversity_penalty * seen
            if adjusted > best_adjusted_score:
                best_adjusted_score = adjusted
                best_idx = idx
        if best_idx < 0:
            break
        chosen = remaining.pop(best_idx)
        note_counts[str(chosen.get("note_path") or "")] += 1
        selected.append(chosen)
    return selected


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
