from __future__ import annotations

from pathlib import Path

from app.config import AppSettings
from evaluation.cs_reference_eval import (
    build_basename_index,
    build_cs_eval_dataset,
    clean_note_text,
    collect_markdown_paths,
    resolve_note_target,
)


def test_build_cs_eval_dataset_uses_copied_notes_and_keeps_vault_read_only(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    cs = vault / "cs"
    other = vault / "other"
    cs.mkdir(parents=True)
    other.mkdir(parents=True)

    kept = cs / "keep.md"
    dropped = cs / "drop.md"
    target = cs / "target.md"
    external = other / "outside.md"

    kept.write_text("link [[target]] and ![[diagram.png]]", encoding="utf-8")
    dropped.write_text("external [[outside]]", encoding="utf-8")
    target.write_text("target body", encoding="utf-8")
    external.write_text("outside body", encoding="utf-8")

    original_keep = kept.read_text(encoding="utf-8")
    settings = AppSettings(vault_path=vault, sqlite_path=tmp_path / "meta.db", embedding_api_key=None)

    dataset = build_cs_eval_dataset(settings, tmp_path / "work")

    assert kept.read_text(encoding="utf-8") == original_keep
    assert "cs/keep.md" in dataset["kept_notes"]
    assert "cs/drop.md" not in dataset["kept_notes"]
    assert any(item["note_path"] == "cs/drop.md" for item in dataset["dropped_notes"])

    clean_keep = (tmp_path / "work" / "clean_vault" / "cs" / "keep.md").read_text(encoding="utf-8")
    assert "[[target]]" not in clean_keep
    assert "![[diagram.png]]" in clean_keep
    assert "link target" in clean_keep


def test_clean_note_text_only_strips_markdown_note_links() -> None:
    raw = """---
tags: [demo]
---
body [[Target Note#Section]] and [Local](folder/doc.md) and ![[image.png]]
"""

    cleaned = clean_note_text(raw)

    assert "[[Target Note#Section]]" not in cleaned
    assert "[Local](folder/doc.md)" not in cleaned
    assert "![[image.png]]" in cleaned
    assert "Target Note" in cleaned
    assert "Local" in cleaned


def test_resolve_note_target_prefers_relative_then_unique_basename(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    cs = vault / "cs"
    (cs / "sub").mkdir(parents=True)
    (cs / "sub" / "a.md").write_text("", encoding="utf-8")
    (cs / "sub" / "b.md").write_text("", encoding="utf-8")
    (cs / "other.md").write_text("", encoding="utf-8")

    notes = collect_markdown_paths(vault)
    basename_index = build_basename_index(notes)

    relative = resolve_note_target("cs/sub/a.md", "b", notes, basename_index)
    unique_basename = resolve_note_target("cs/sub/a.md", "other", notes, basename_index)

    assert relative.status == "resolved_internal"
    assert relative.resolved_path == "cs/sub/b.md"
    assert unique_basename.status == "resolved_internal"
    assert unique_basename.resolved_path == "cs/other.md"


def test_resolve_note_target_does_not_guess_ambiguous_basename(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    (vault / "cs" / "a").mkdir(parents=True)
    (vault / "cs" / "b").mkdir(parents=True)
    (vault / "cs" / "a" / "shared.md").write_text("", encoding="utf-8")
    (vault / "cs" / "b" / "shared.md").write_text("", encoding="utf-8")
    (vault / "cs" / "source.md").write_text("", encoding="utf-8")

    notes = collect_markdown_paths(vault)
    basename_index = build_basename_index(notes)
    result = resolve_note_target("cs/source.md", "shared", notes, basename_index)

    assert result.status == "ambiguous_note_target"
