from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class LinkRef:
    src_note_path: str
    src_block_uid: str | None
    dst_note_path: str
    dst_heading: str | None
    dst_block_id: str | None
    link_text: str | None
    link_type: str


@dataclass(slots=True)
class Block:
    block_uid: str
    note_path: str
    block_id: str
    heading_path: list[str]
    raw_text: str
    clean_text: str
    char_start: int
    char_end: int
    token_count_est: int
    block_hash: str
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NoteDoc:
    path: str
    title: str
    aliases: list[str]
    tags: list[str]
    frontmatter: dict[str, Any]
    body: str
    content_hash: str
    mtime: float
    blocks: list[Block] = field(default_factory=list)
    links: list[LinkRef] = field(default_factory=list)
