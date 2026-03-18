from __future__ import annotations

from pathlib import Path

from indexing.parser import parse_markdown_file
from indexing.splitter import split_note_into_blocks
from app.config import BlockSplitConfig


def test_parse_links_and_block_ids(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    md = vault / "demo.md"
    md.write_text(
        """---
tags: [privacy]
aliases: [DemoAlias]
---
# Title
paragraph [[Target#Section]] and ![[Other#^bid|Show]]

- item text ^item1
""",
        encoding="utf-8",
    )
    note = parse_markdown_file(md, vault)
    assert note.title == "demo"
    assert "privacy" in note.tags
    assert len(note.links) >= 2
    blocks = split_note_into_blocks(note, BlockSplitConfig(min_chars=1, max_chars=200))
    assert any("auto-" in b.block_id or b.block_id == "item1" for b in blocks)
