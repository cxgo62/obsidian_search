from __future__ import annotations

import json
import os
import re
import shutil
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

import frontmatter

from app.container import build_container_from_settings
from app.config import AppSettings, load_settings
from indexing.cleaner import MD_LINK_RE
from indexing.parser import WIKILINK_RE

SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


@dataclass(slots=True)
class EvalPaths:
    work_root: Path
    source_vault: Path
    clean_vault: Path
    reports_dir: Path
    sqlite_path: Path
    milvus_path: Path


@dataclass(slots=True)
class ResolutionResult:
    status: str
    resolved_path: str | None = None
    normalized_target: str | None = None


@dataclass(slots=True)
class EvaluationMetrics:
    dataset_note_count: int
    candidate_note_count: int
    avg_gt_links_per_note: float
    hit_at_5: float
    hit_at_10: float
    recall_at_5: float
    recall_at_10: float
    precision_at_5: float
    precision_at_10: float
    mrr: float
    coverage: float


def eval_paths(work_root: Path) -> EvalPaths:
    return EvalPaths(
        work_root=work_root,
        source_vault=work_root / "source_copy",
        clean_vault=work_root / "clean_vault",
        reports_dir=work_root / "reports",
        sqlite_path=work_root / "meta.db",
        milvus_path=work_root / "milvus.db",
    )


def build_cs_eval_dataset(settings: AppSettings, work_root: Path) -> dict[str, Any]:
    paths = eval_paths(work_root)
    prepare_workspace(paths)
    copy_cs_markdown(settings.vault_path, paths.source_vault)

    full_vault_notes = collect_markdown_paths(settings.vault_path)
    cs_notes = collect_markdown_paths(paths.source_vault)
    basename_index = build_basename_index(full_vault_notes)

    kept_notes: list[str] = []
    evaluation_notes: list[str] = []
    dropped_notes: list[dict[str, Any]] = []
    ground_truth_entries: list[dict[str, Any]] = []

    for note_path in sorted(cs_notes):
        raw_text = (paths.source_vault / note_path).read_text(encoding="utf-8")
        references = analyze_note_references(note_path, raw_text, full_vault_notes, basename_index)
        if references["external_markdown_refs"]:
            dropped_notes.append(
                {
                    "note_path": note_path,
                    "external_markdown_refs": references["external_markdown_refs"],
                }
            )
            continue

        kept_notes.append(note_path)
        if references["targets"]:
            evaluation_notes.append(note_path)

        dest = paths.clean_vault / note_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(clean_note_text(raw_text), encoding="utf-8")
        ground_truth_entries.append(
            {
                "note_path": note_path,
                "targets": references["targets"],
                "target_count": len(references["targets"]),
                "ignored_links": references["ignored_links"],
                "resolved_internal_links": references["resolved_internal_links"],
            }
        )

    dataset = {
        "source_vault": str(paths.source_vault),
        "clean_vault": str(paths.clean_vault),
        "kept_note_count": len(kept_notes),
        "evaluation_note_count": len(evaluation_notes),
        "dropped_note_count": len(dropped_notes),
        "kept_notes": kept_notes,
        "evaluation_notes": evaluation_notes,
        "dropped_notes": dropped_notes,
        "ground_truth": ground_truth_entries,
    }
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    (paths.reports_dir / "ground_truth.json").write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
    return dataset


def analyze_note_references(
    note_path: str,
    raw_text: str,
    full_vault_notes: set[str],
    basename_index: dict[str, list[str]],
) -> dict[str, Any]:
    targets: set[str] = set()
    resolved_internal_links: list[dict[str, str]] = []
    external_markdown_refs: list[dict[str, str]] = []
    ignored_links: list[dict[str, str]] = []

    for raw_target in extract_raw_targets(raw_text):
        resolution = resolve_note_target(note_path, raw_target, full_vault_notes, basename_index)
        if resolution.status == "resolved_internal":
            assert resolution.resolved_path is not None
            if resolution.resolved_path != note_path:
                targets.add(resolution.resolved_path)
            resolved_internal_links.append(
                {
                    "raw_target": raw_target,
                    "resolved_path": resolution.resolved_path,
                }
            )
        elif resolution.status == "resolved_external":
            external_markdown_refs.append(
                {
                    "raw_target": raw_target,
                    "resolved_path": resolution.resolved_path or "",
                }
            )
        else:
            ignored_links.append(
                {
                    "raw_target": raw_target,
                    "reason": resolution.status,
                }
            )

    return {
        "targets": sorted(targets),
        "resolved_internal_links": resolved_internal_links,
        "external_markdown_refs": external_markdown_refs,
        "ignored_links": ignored_links,
    }


def prepare_workspace(paths: EvalPaths) -> None:
    if paths.work_root.exists():
        shutil.rmtree(paths.work_root)
    paths.source_vault.mkdir(parents=True, exist_ok=True)
    paths.clean_vault.mkdir(parents=True, exist_ok=True)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)


def copy_cs_markdown(vault_path: Path, dest_vault_root: Path) -> list[str]:
    cs_root = vault_path / "cs"
    copied: list[str] = []
    for src in sorted(cs_root.rglob("*.md")):
        rel = src.relative_to(vault_path)
        dest = dest_vault_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(str(rel))
    return copied


def collect_markdown_paths(vault_root: Path) -> set[str]:
    return {str(path.relative_to(vault_root)) for path in vault_root.rglob("*.md")}


def build_basename_index(note_paths: set[str]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for note_path in sorted(note_paths):
        index.setdefault(PurePosixPath(note_path).name, []).append(note_path)
    return index


def extract_raw_targets(raw_text: str) -> list[str]:
    body = frontmatter.loads(raw_text).content
    out: list[str] = []
    for match in WIKILINK_RE.finditer(body):
        content = match.group(2).strip()
        target = content.split("|", 1)[0].strip()
        if target:
            out.append(target)
    for match in MD_LINK_RE.finditer(body):
        href = (match.group(2) or match.group(4) or "").strip()
        if href:
            out.append(href)
    return out


def resolve_note_target(
    src_note_path: str,
    raw_target: str,
    full_vault_notes: set[str],
    basename_index: dict[str, list[str]],
) -> ResolutionResult:
    normalized = normalize_note_target(raw_target)
    if normalized is None:
        return ResolutionResult(status=classify_target(raw_target))

    for candidate in build_resolution_candidates(src_note_path, normalized):
        if candidate in full_vault_notes:
            status = "resolved_internal" if candidate.startswith("cs/") else "resolved_external"
            return ResolutionResult(status=status, resolved_path=candidate, normalized_target=normalized)

    basename_matches = basename_index.get(PurePosixPath(normalized).name, [])
    if len(basename_matches) == 1:
        candidate = basename_matches[0]
        status = "resolved_internal" if candidate.startswith("cs/") else "resolved_external"
        return ResolutionResult(status=status, resolved_path=candidate, normalized_target=normalized)
    if len(basename_matches) > 1:
        return ResolutionResult(status="ambiguous_note_target", normalized_target=normalized)
    return ResolutionResult(status="unresolved_note_target", normalized_target=normalized)


def classify_target(raw_target: str) -> str:
    target = raw_target.strip()
    if not target:
        return "empty_target"
    if SCHEME_RE.match(target):
        return "external_scheme"
    parsed = urlparse(target)
    if parsed.scheme:
        return "external_scheme"
    target = split_target_anchor(target)
    if not target:
        return "same_note_anchor"
    suffix = PurePosixPath(target).suffix.lower()
    if suffix and suffix != ".md":
        return "non_markdown_target"
    return "markdown_note_target"


def normalize_note_target(raw_target: str) -> str | None:
    if classify_target(raw_target) != "markdown_note_target":
        return None
    target = split_target_anchor(raw_target.strip())
    if not target:
        return None
    normalized = target if target.lower().endswith(".md") else f"{target}.md"
    return normalized.lstrip("/")


def split_target_anchor(target: str) -> str:
    if "#^" in target:
        return target.split("#^", 1)[0].strip()
    if "#" in target:
        return target.split("#", 1)[0].strip()
    return target.strip()


def build_resolution_candidates(src_note_path: str, normalized_target: str) -> list[str]:
    candidates: list[str] = []
    src_dir = PurePosixPath(src_note_path).parent
    if normalized_target.startswith("cs/"):
        candidates.append(normalized_target)
    else:
        candidates.append((src_dir / normalized_target).as_posix())
        candidates.append(f"cs/{normalized_target}")
        candidates.append(normalized_target)
    deduped: list[str] = []
    for item in candidates:
        clean = item.lstrip("/")
        if clean not in deduped:
            deduped.append(clean)
    return deduped


def clean_note_text(raw_text: str) -> str:
    post = frontmatter.loads(raw_text)
    post.content = strip_note_link_syntax(post.content)
    return frontmatter.dumps(post)


def strip_note_link_syntax(body: str) -> str:
    def replace_wikilink(match: re.Match[str]) -> str:
        raw_target = match.group(2).strip().split("|", 1)[0].strip()
        if normalize_note_target(raw_target) is None:
            return match.group(0)
        content = match.group(2).strip()
        if "|" in content:
            return content.split("|", 1)[1].strip()
        base = split_target_anchor(raw_target)
        return PurePosixPath(base).stem or base

    def replace_md_link(match: re.Match[str]) -> str:
        whole = match.group(0)
        alt_text = match.group(1)
        image_href = match.group(2)
        label = match.group(3)
        href = match.group(4)
        raw_target = (image_href or href or "").strip()
        if normalize_note_target(raw_target) is None:
            return whole
        visible = (alt_text or label or "").strip()
        if visible:
            return visible
        base = split_target_anchor(raw_target)
        return PurePosixPath(base).stem or base

    text = WIKILINK_RE.sub(replace_wikilink, body)
    text = MD_LINK_RE.sub(replace_md_link, text)
    return text


def run_cs_reference_eval(
    settings: AppSettings | None = None,
    work_root: Path | None = None,
    retrieval_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or load_settings()
    work_root = work_root or Path("tmp/cs_eval")
    if retrieval_overrides:
        settings.retrieval = settings.retrieval.model_copy(update=retrieval_overrides)
    paths = eval_paths(work_root)
    dataset = build_cs_eval_dataset(settings, work_root)

    with temporary_env(
        {
            "OBS_VAULT_PATH": str(paths.clean_vault),
            "OBS_SQLITE_PATH": str(paths.sqlite_path),
            "OBS_MILVUS_URI": str(paths.milvus_path),
            "OBS_MILVUS_COLLECTION": "obsidian_blocks_cs_eval",
        }
    ):
        runtime_settings = settings.model_copy(
            update={
                "vault_path": paths.clean_vault,
                "sqlite_path": paths.sqlite_path,
                "milvus_uri": str(paths.milvus_path),
                "milvus_collection": "obsidian_blocks_cs_eval",
            }
        )
        container = build_container_from_settings(runtime_settings)
        try:
            container.sync_service.rebuild()
            predictions = evaluate_notes(container.query_service, dataset["ground_truth"])
        finally:
            container.sqlite_repo.close()

    metrics = compute_metrics(predictions)
    report = {
        "dataset": {
            "source_vault": dataset["source_vault"],
            "clean_vault": dataset["clean_vault"],
            "kept_note_count": dataset["kept_note_count"],
            "evaluation_note_count": dataset["evaluation_note_count"],
            "dropped_note_count": dataset["dropped_note_count"],
        },
        "retrieval_config": settings.retrieval.model_dump(),
        "metrics": asdict(metrics),
        "predictions": predictions,
        "dropped_notes": dataset["dropped_notes"],
    }
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    (paths.reports_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (paths.reports_dir / "report.md").write_text(render_markdown_report(report), encoding="utf-8")
    return report


def evaluate_notes(query_service: Any, ground_truth_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predictions: list[dict[str, Any]] = []
    for entry in ground_truth_entries:
        if not entry["targets"]:
            continue
        result = query_service.query_note(entry["note_path"])
        predicted_notes = [item["note_path"] for item in result["note_summary"]["related_notes"]]
        predictions.append(
            {
                "note_path": entry["note_path"],
                "targets": entry["targets"],
                "predicted_notes": predicted_notes,
                "top_5": predicted_notes[:5],
                "top_10": predicted_notes[:10],
                "hits_5": sorted(set(entry["targets"]) & set(predicted_notes[:5])),
                "hits_10": sorted(set(entry["targets"]) & set(predicted_notes[:10])),
                "misses_10": sorted(set(entry["targets"]) - set(predicted_notes[:10])),
                "false_positives_10": sorted(set(predicted_notes[:10]) - set(entry["targets"])),
            }
        )
    return predictions


def compute_metrics(predictions: list[dict[str, Any]]) -> EvaluationMetrics:
    if not predictions:
        return EvaluationMetrics(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    total_notes = len(predictions)
    gt_counts = [len(item["targets"]) for item in predictions]
    hit_5 = 0
    hit_10 = 0
    recall_5 = 0.0
    recall_10 = 0.0
    precision_5 = 0.0
    precision_10 = 0.0
    reciprocal_rank = 0.0
    covered = 0
    candidate_notes: set[str] = set()

    for item in predictions:
        targets = set(item["targets"])
        top_5 = item["predicted_notes"][:5]
        top_10 = item["predicted_notes"][:10]
        candidate_notes.update(item["predicted_notes"])
        top_5_hits = targets & set(top_5)
        top_10_hits = targets & set(top_10)
        if top_5_hits:
            hit_5 += 1
        if top_10_hits:
            hit_10 += 1
            covered += 1
        recall_5 += len(top_5_hits) / max(len(targets), 1)
        recall_10 += len(top_10_hits) / max(len(targets), 1)
        precision_5 += len(top_5_hits) / max(len(top_5), 1)
        precision_10 += len(top_10_hits) / max(len(top_10), 1)
        reciprocal_rank += reciprocal_rank_for_targets(item["predicted_notes"], targets)

    return EvaluationMetrics(
        dataset_note_count=total_notes,
        candidate_note_count=len(candidate_notes),
        avg_gt_links_per_note=sum(gt_counts) / max(total_notes, 1),
        hit_at_5=hit_5 / total_notes,
        hit_at_10=hit_10 / total_notes,
        recall_at_5=recall_5 / total_notes,
        recall_at_10=recall_10 / total_notes,
        precision_at_5=precision_5 / total_notes,
        precision_at_10=precision_10 / total_notes,
        mrr=reciprocal_rank / total_notes,
        coverage=covered / total_notes,
    )


def reciprocal_rank_for_targets(predicted_notes: list[str], targets: set[str]) -> float:
    for idx, note_path in enumerate(predicted_notes, start=1):
        if note_path in targets:
            return 1.0 / idx
    return 0.0


def render_markdown_report(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    worst_misses = sorted(report["predictions"], key=lambda item: (len(item["hits_10"]), -len(item["misses_10"])))[:10]
    worst_false_positives = sorted(report["predictions"], key=lambda item: -len(item["false_positives_10"]))[:10]
    lines = [
        "# CS Reference Evaluation Report",
        "",
        "## Dataset",
        f"- kept_note_count: {report['dataset']['kept_note_count']}",
        f"- evaluation_note_count: {report['dataset']['evaluation_note_count']}",
        f"- dropped_note_count: {report['dataset']['dropped_note_count']}",
        "",
        "## Metrics",
        f"- dataset_note_count: {metrics['dataset_note_count']}",
        f"- avg_gt_links_per_note: {metrics['avg_gt_links_per_note']:.4f}",
        f"- hit_at_5: {metrics['hit_at_5']:.4f}",
        f"- hit_at_10: {metrics['hit_at_10']:.4f}",
        f"- recall_at_5: {metrics['recall_at_5']:.4f}",
        f"- recall_at_10: {metrics['recall_at_10']:.4f}",
        f"- precision_at_5: {metrics['precision_at_5']:.4f}",
        f"- precision_at_10: {metrics['precision_at_10']:.4f}",
        f"- mrr: {metrics['mrr']:.4f}",
        f"- coverage: {metrics['coverage']:.4f}",
        "",
        "## Worst Misses",
    ]
    for item in worst_misses:
        lines.append(
            f"- {item['note_path']}: hits_10={len(item['hits_10'])}, misses_10={','.join(item['misses_10'][:5])}"
        )
    lines.extend(["", "## False Positives"])
    for item in worst_false_positives:
        lines.append(
            f"- {item['note_path']}: false_positives_10={','.join(item['false_positives_10'][:5])}"
        )
    return "\n".join(lines) + "\n"


@contextmanager
def temporary_env(values: dict[str, str]) -> Any:
    old_values = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            os.environ[key] = value
        yield
    finally:
        for key, old in old_values.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
