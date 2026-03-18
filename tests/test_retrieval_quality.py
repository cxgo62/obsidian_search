from __future__ import annotations

from app.config import BlockSplitConfig, RetrievalConfig
from app.models import Block, NoteDoc
from indexing.splitter import build_embedding_inputs
from query.ranker import fuse_scores
from storage.sqlite_repo import SQLiteRepo


def test_fuse_scores_limits_repeated_hits_from_same_note() -> None:
    cfg = RetrievalConfig(top_k=2, threshold=0.0, max_hits_per_note=1, note_diversity_penalty=0.1)
    semantic = [
        {"block_uid": "a1", "note_path": "A.md", "semantic_score": 0.92},
        {"block_uid": "a2", "note_path": "A.md", "semantic_score": 0.90},
        {"block_uid": "b1", "note_path": "B.md", "semantic_score": 0.87},
    ]
    fused = fuse_scores(semantic, [], {}, cfg)
    assert len(fused) == 2
    assert [h["note_path"] for h in fused] == ["A.md", "B.md"]


def test_build_embedding_inputs_sliding_includes_context() -> None:
    blocks = [
        _mk_block("n.md:b1", "n.md", ["Topic"], "alpha ideas", 0),
        _mk_block("n.md:b2", "n.md", ["Topic"], "beta details", 10),
        _mk_block("n.md:b3", "n.md", ["Topic"], "gamma analysis", 20),
    ]
    cfg = BlockSplitConfig(window_mode="SLIDING", window_neighbors=1)
    inputs = build_embedding_inputs(blocks, cfg)
    assert len(inputs) == 3
    assert "Current: beta details" in inputs[1]
    assert "Neighbor: alpha ideas" in inputs[1]
    assert "Neighbor: gamma analysis" in inputs[1]


def test_lexical_search_filters_high_frequency_common_terms(tmp_path) -> None:
    repo = SQLiteRepo(tmp_path / "meta.db")
    _insert_note(
        repo,
        "common.md",
        [f"api http 接口 管理 基础说明 {i}" for i in range(12)],
    )
    _insert_note(
        repo,
        "deep.md",
        ["oauth2 refresh token rotation and session hardening"],
    )

    hits = repo.lexical_search("api oauth2", top_k=5)
    assert hits
    assert hits[0]["note_path"] == "deep.md"
    repo.close()


def _insert_note(repo: SQLiteRepo, note_path: str, texts: list[str]) -> None:
    note = NoteDoc(
        path=note_path,
        title=note_path,
        aliases=[],
        tags=[],
        frontmatter={},
        body="\n\n".join(texts),
        content_hash=f"hash-{note_path}",
        mtime=0.0,
    )
    blocks = [_mk_block(f"{note_path}:b{i}", note_path, [], text, i * 100) for i, text in enumerate(texts)]
    repo.upsert_note(note)
    repo.replace_note_blocks(note_path, blocks)


def _mk_block(uid: str, note_path: str, headings: list[str], text: str, start: int) -> Block:
    return Block(
        block_uid=uid,
        note_path=note_path,
        block_id=uid.rsplit(":", 1)[-1],
        heading_path=headings,
        raw_text=text,
        clean_text=text,
        char_start=start,
        char_end=start + len(text),
        token_count_est=max(1, len(text) // 4),
        block_hash=f"hash-{uid}",
    )
