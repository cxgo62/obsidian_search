# Hybrid Retrieval Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the user-facing `search()` retrieval pipeline so it closes more of the quality gap versus "send full text to the LLM" while keeping token usage bounded.

**Architecture:** Keep the existing Milvus + SQLite hybrid retriever, but add three missing layers: query expansion, stronger reranking, and evidence compression. Stage the rollout so Phase 1 only changes `search()` and the existing numeric score contract remains intact; defer `query_note()` fan-out and heavier answer-side work until the lower-risk search path is validated.

**Tech Stack:** Python, FastAPI, Pydantic settings, SQLite FTS5, Milvus Lite, pytest

---

## File Structure

**Existing files to modify**
- `src/app/config.py`
- `src/query/retriever.py`
- `src/query/service.py`
- `src/query/ranker.py`
- `src/indexing/splitter.py`
- `scripts/run_cs_reference_eval.py`
- `tests/test_retrieval_quality.py`

**New files to create**
- `src/query/query_expansion.py`
- `src/query/evidence.py`
- `tests/test_query_expansion.py`
- `tests/test_evidence.py`

**Responsibility boundaries**
- `src/query/query_expansion.py`: Generate multiple retrieval-ready subqueries from one user query without depending on online LLM calls.
- `src/query/retriever.py`: Run one or many retrieval passes and return candidates in a format that preserves semantic and lexical score semantics.
- `src/query/ranker.py`: Handle fusion and reciprocal-rank-style aggregation without breaking existing score explainability.
- `src/query/evidence.py`: Compress retrieved blocks into a smaller answer-ready evidence set.
- `src/query/service.py`: Orchestrate end-to-end search flow and expose explainability fields.
- `src/indexing/splitter.py`: Improve chunk boundaries and optional overlap handling.

## Scope Guardrails

- Phase 1 targets `QueryService.search()` only.
- `query_note()` and `query_block()` stay on the current single-query path unless Phase 1 shows clear gains and acceptable latency.
- Multi-query aggregation must preserve the current `fuse_scores()` input contract. Rank-based merging may be used for candidate selection, but `semantic_score` and `lex_score` passed into fusion must remain calibrated numeric scores rather than opaque RRF totals.
- Evidence compression is treated as a search-response optimization in this plan, not as a substitute for retrieval eval. It needs its own lightweight acceptance checks.

### Task 1: Baseline Lock-In

**Files:**
- Modify: `scripts/run_cs_reference_eval.py`
- Modify: `tests/test_retrieval_quality.py`

- [ ] **Step 1: Add regression-oriented baseline tests**

```python
def test_fuse_scores_prefers_multi_signal_hits() -> None:
    cfg = RetrievalConfig(top_k=3, threshold=0.0)
    semantic = [{"block_uid": "a", "note_path": "a.md", "semantic_score": 0.9}]
    lexical = [{"block_uid": "a", "note_path": "a.md", "lex_score": 0.8}]
    fused = fuse_scores(semantic, lexical, {}, cfg)
    assert fused[0]["block_uid"] == "a"
    assert fused[0]["semantic_lexical_synergy"] > 0

def test_search_path_uses_single_query_by_default() -> None:
    ...
    assert expansion_calls == []
```

- [ ] **Step 2: Run test to verify current baseline is stable**

Run: `pytest tests/test_retrieval_quality.py -v`
Expected: PASS and existing retrieval tests remain green.

- [ ] **Step 3: Extend eval script output to print active retrieval mode flags**

```python
print(json.dumps({
    "metrics": report["metrics"],
    "retrieval_config": report["retrieval_config"],
}, ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Run the eval script once and capture the current baseline**

Run: `PYTHONPATH=src .venv/bin/python scripts/run_cs_reference_eval.py --work-root tmp/cs_eval_baseline`
Expected: JSON output with metrics and report paths.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_cs_reference_eval.py tests/test_retrieval_quality.py
git commit -m "test: lock retrieval baseline"
```

### Task 2: Multi-Query Expansion

**Files:**
- Create: `src/query/query_expansion.py`
- Modify: `src/app/config.py`
- Test: `tests/test_query_expansion.py`

- [ ] **Step 1: Write failing tests for deterministic query expansion**

```python
def test_expand_query_generates_keyword_and_original_variants() -> None:
    variants = expand_query("oauth2 refresh token rotation 原理", QueryExpansionConfig())
    texts = [item.text for item in variants]
    assert texts[0] == "oauth2 refresh token rotation 原理"
    assert any("oauth2 refresh token rotation" in text for text in texts)
    assert len(texts) >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_expansion.py -v`
Expected: FAIL because `expand_query` and config do not exist yet.

- [ ] **Step 3: Add query expansion config**

```python
class QueryExpansionConfig(BaseModel):
    enabled: bool = True
    max_variants: int = 4
    min_token_length: int = 2
```

- [ ] **Step 4: Implement deterministic expansion logic**

```python
@dataclass(slots=True)
class QueryVariant:
    text: str
    source: str
    weight: float
```

Implementation notes:
- Always include original query.
- Build a keyword-only variant using informative tokens.
- Build a title-style compact variant for long natural-language questions.
- Deduplicate variants by normalized text.
- Keep expansion deterministic and side-effect free so it is easy to benchmark.

- [ ] **Step 5: Run tests to verify expansion passes**

Run: `pytest tests/test_query_expansion.py tests/test_retrieval_quality.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/app/config.py src/query/query_expansion.py tests/test_query_expansion.py tests/test_retrieval_quality.py
git commit -m "feat: add deterministic query expansion"
```

### Task 3: Multi-Query Retrieval Merge

**Files:**
- Modify: `src/query/retriever.py`
- Modify: `src/query/ranker.py`
- Modify: `src/query/service.py`
- Test: `tests/test_retrieval_quality.py`

- [ ] **Step 1: Write a failing test for multi-query candidate merging**

```python
def test_candidate_merge_promotes_hits_seen_in_multiple_variants() -> None:
    merged = merge_candidate_lists([
        [
            {"block_uid": "a", "semantic_score": 0.91},
            {"block_uid": "c", "semantic_score": 0.89},
        ],
        [
            {"block_uid": "b", "semantic_score": 0.93},
            {"block_uid": "a", "semantic_score": 0.88},
        ],
    ])
    assert merged[0]["block_uid"] == "a"
    assert merged[0]["semantic_score"] >= 0.91
```

- [ ] **Step 2: Run targeted test to verify it fails**

Run: `pytest tests/test_retrieval_quality.py::test_rrf_merge_rewards_hits_seen_in_multiple_variants -v`
Expected: FAIL because the merge helper does not exist.

- [ ] **Step 3: Implement candidate merge helper in ranker**

```python
def merge_candidate_lists(rank_lists: list[list[dict[str, Any]]], *, score_key: str) -> list[dict[str, Any]]:
    ...
    ...
```

- [ ] **Step 4: Update retriever to support many query variants**

Implementation notes:
- Add `retrieve_for_queries(queries: list[str], top_k_ann: int | None, exclude_note: str | None)`.
- For each query variant, run semantic and lexical retrieval.
- Merge semantic lists separately from lexical lists before fusion.
- Preserve score semantics by aggregating per-candidate scores with `max()` or a bounded weighted blend, not by replacing them with raw RRF totals.
- Use rank-based logic only to decide candidate retention order before score fusion.

- [ ] **Step 5: Update `QueryService.search` to use expanded variants**

Implementation notes:
- Gate behind `settings.retrieval.query_expansion.enabled`.
- Restrict Phase 1 rollout to `search()` only.
- Preserve explain fields so the API still shows semantic and lexical scores.

- [ ] **Step 6: Add a latency guard test or benchmark hook**

Implementation notes:
- Capture number of embedder calls and retrieval fan-out for one `search()` request.
- Document expected upper bound: `max_variants * 2` retrieval passes for semantic and lexical combined logic.

- [ ] **Step 7: Run retrieval tests**

Run: `pytest tests/test_retrieval_quality.py tests/test_query_expansion.py -v`
Expected: PASS

- [ ] **Step 8: Run eval and compare to baseline**

Run: `PYTHONPATH=src .venv/bin/python scripts/run_cs_reference_eval.py --work-root tmp/cs_eval_multi_query`
Expected: Metrics are produced; improvement target is better `hit_at_5` and `mrr` than baseline.

- [ ] **Step 9: Commit**

```bash
git add src/query/retriever.py src/query/ranker.py src/query/service.py tests/test_retrieval_quality.py
git commit -m "feat: add multi-query retrieval merge"
```

### Task 4: Soften Anchor Filtering Before Adding More Answer-Side Logic

**Files:**
- Modify: `src/query/service.py`
- Modify: `tests/test_retrieval_quality.py`

- [ ] **Step 1: Write a failing test for semantic paraphrase preservation**

```python
def test_anchor_rerank_does_not_drop_semantic_hit_with_low_token_overlap() -> None:
    ...
    assert reranked
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieval_quality.py::test_anchor_rerank_does_not_drop_semantic_hit_with_low_token_overlap -v`
Expected: FAIL because the current logic drops the hit.

- [ ] **Step 3: Change anchor rerank from hard `continue` filters to additive or multiplicative soft penalties**

Implementation notes:
- Never drop solely on low overlap.
- Keep `content_anchor` as an explainability feature.
- Apply stronger penalty only when semantic, lexical, and graph signals are all weak.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_retrieval_quality.py -v`
Expected: PASS

- [ ] **Step 5: Run eval**

Run: `PYTHONPATH=src .venv/bin/python scripts/run_cs_reference_eval.py --work-root tmp/cs_eval_soft_anchor`
Expected: Better coverage than the current hard-filter path.

- [ ] **Step 6: Commit**

```bash
git add src/query/service.py tests/test_retrieval_quality.py
git commit -m "feat: soften anchor rerank penalties"
```

### Task 5: Evidence Compression Layer With Independent Acceptance Checks

**Files:**
- Create: `src/query/evidence.py`
- Modify: `src/app/config.py`
- Modify: `src/query/service.py`
- Test: `tests/test_evidence.py`

- [ ] **Step 1: Write failing tests for evidence compression**

```python
def test_select_evidence_limits_duplicate_context_from_same_note() -> None:
    ...
    assert [row["note_path"] for row in evidence] == ["a.md", "b.md"]

def test_select_evidence_prefers_topical_diversity_over_adjacent_duplicates() -> None:
    ...
    assert evidence[0]["block_uid"] != evidence[1]["block_uid"]
```

- [ ] **Step 2: Run targeted test to verify it fails**

Run: `pytest tests/test_evidence.py -v`
Expected: FAIL because evidence selection does not exist.

- [ ] **Step 3: Add evidence config**

```python
class EvidenceConfig(BaseModel):
    enabled: bool = True
    max_items: int = 8
    max_per_note: int = 2
    snippet_chars: int = 280
```

- [ ] **Step 4: Implement evidence selection and compression**

Implementation notes:
- Input is enriched hits from `QueryService.search()`.
- Prefer high-score hits with note diversity.
- Keep compact snippets and headings.
- Return an `evidence` array in API responses in addition to raw `matches`.
- Do not wire this into `query_note()` yet.

- [ ] **Step 5: Add an acceptance script or test fixture for answer-ready context**

Implementation notes:
- Build a small fixed fixture of query -> hits -> expected evidence ordering.
- Verify evidence output stays within configured item and snippet limits.
- Treat this as the acceptance gate for Task 5, since CS reference eval does not measure evidence quality.

- [ ] **Step 6: Wire evidence output into the `search()` response**

```python
return {
    "query": text,
    "matches": enriched_hits,
    "evidence": build_evidence(enriched_hits, self._settings.retrieval.evidence),
}
```

- [ ] **Step 7: Run tests**

Run: `pytest tests/test_evidence.py tests/test_retrieval_quality.py -v`
Expected: PASS

- [ ] **Step 8: Manually inspect one search response**

Run: `PYTHONPATH=src .venv/bin/python - <<'PY'`
Expected: One serialized search response showing both `matches` and compact `evidence`.

- [ ] **Step 9: Commit**

```bash
git add src/app/config.py src/query/evidence.py src/query/service.py tests/test_evidence.py
git commit -m "feat: add evidence compression output"
```

### Task 6: Hierarchical Chunking Improvements

**Files:**
- Modify: `src/indexing/splitter.py`
- Modify: `src/app/config.py`
- Modify: `tests/test_retrieval_quality.py`

- [ ] **Step 1: Write a failing test for paragraph-aware chunking**

```python
def test_splitter_preserves_paragraph_boundaries_when_splitting_long_blocks() -> None:
    ...
    assert blocks[0].clean_text.endswith("。")
    assert blocks[1].clean_text.startswith("第二段")
```

- [ ] **Step 2: Run targeted test to verify it fails**

Run: `pytest tests/test_retrieval_quality.py::test_splitter_preserves_paragraph_boundaries_when_splitting_long_blocks -v`
Expected: FAIL with current fixed-width chunking.

- [ ] **Step 3: Extend split config for overlap and paragraph-aware splitting**

```python
class BlockSplitConfig(BaseModel):
    ...
    split_overlap_chars: int = 120
    prefer_paragraph_boundary: bool = True
```

- [ ] **Step 4: Implement boundary-aware splitting**

Implementation notes:
- Prefer splitting at blank lines or sentence boundaries before `max_chars`.
- Add overlap between adjacent split chunks.
- Keep heading context attached to embedding input.
- Do not change note-level chunk identity semantics more than necessary; existing block IDs should remain stable for unsplit blocks.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_retrieval_quality.py -v`
Expected: PASS

- [ ] **Step 6: Reindex and run eval**

Run: `PYTHONPATH=src .venv/bin/python scripts/run_cs_reference_eval.py --work-root tmp/cs_eval_hierarchical_chunks`
Expected: Metric output; inspect whether recall improves on long-note references.

- [ ] **Step 7: Commit**

```bash
git add src/app/config.py src/indexing/splitter.py tests/test_retrieval_quality.py
git commit -m "feat: improve chunk boundary handling"
```

### Task 7: Final Evaluation and Default Rollout

**Files:**
- Modify: `config.json`
- Modify: `scripts/run_cs_reference_eval.py`

- [ ] **Step 1: Compare all eval outputs and choose the best-performing flag set**

Run: `rg -n '"hit_at_5"|"mrr"|"coverage"' tmp/cs_eval_* tmp/*/reports/report.json -S`
Expected: Quick summary of candidate runs.

- [ ] **Step 2: Promote winning settings into `config.json` defaults**

Implementation notes:
- Only enable features that improved eval or online quality.
- Keep riskier changes configurable.

- [ ] **Step 3: Run smoke tests**

Run: `pytest tests/test_query_expansion.py tests/test_evidence.py tests/test_retrieval_quality.py -v`
Expected: PASS

- [ ] **Step 4: Run one final eval**

Run: `PYTHONPATH=src .venv/bin/python scripts/run_cs_reference_eval.py --work-root tmp/cs_eval_final`
Expected: Final metrics and report files.

- [ ] **Step 5: Commit**

```bash
git add config.json scripts/run_cs_reference_eval.py
git commit -m "chore: roll out upgraded retrieval defaults"
```

## Success Criteria

- Multi-query retrieval is implemented and enabled behind config.
- Phase 1 multi-query rollout only affects `search()`, unless a follow-up change explicitly expands scope.
- Search responses include a compact evidence payload for downstream LLM answering.
- Hard anchor filtering is removed or softened to avoid false negatives.
- Chunk splitting is more semantic than pure fixed-width slicing.
- The CS reference eval shows measurable improvement on at least one of `hit_at_5`, `mrr`, or `coverage` without a major precision collapse.
- Evidence compression has its own tests or fixtures proving bounded, diverse output even though it is outside the current retrieval eval.

## Notes

- Do not introduce online LLM dependencies in the first pass; keep the first upgrade deterministic and cheap.
- If deterministic query expansion already improves search enough, keep `query_note()` on the old path and defer broader rollout to a follow-up plan.
- If deterministic query expansion and evidence compression already close much of the gap, defer heavier reranker work to a follow-up plan.
- If eval improves but online quality still lags, the next plan should add an optional LLM reranker or answer-side relevance judge.
