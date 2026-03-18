from __future__ import annotations

import hashlib
import re
from dataclasses import replace

from app.config import BlockSplitConfig
from app.models import Block, NoteDoc
from indexing.cleaner import clean_text

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
BLOCK_ID_LINE_RE = re.compile(r"^\^([A-Za-z0-9\-_]+)\s*$")
BLOCK_ID_EOL_RE = re.compile(r"\s\^([A-Za-z0-9\-_]+)\s*$")


def split_note_into_blocks(note: NoteDoc, split_cfg: BlockSplitConfig) -> list[Block]:
    lines = note.body.splitlines(keepends=True)
    blocks: list[Block] = []
    heading_stack: list[str] = []
    buffer: list[str] = []
    block_start_char = 0
    char_cursor = 0
    seq = 0

    def flush_buffer(current_char: int) -> None:
        nonlocal seq, buffer, block_start_char
        if not buffer:
            return
        raw = "".join(buffer).strip("\n")
        if not raw.strip():
            buffer = []
            block_start_char = current_char
            return
        block_id = _detect_block_id(raw, seq)
        cleaned = clean_text(raw)
        if not cleaned:
            buffer = []
            block_start_char = current_char
            return
        uid = f"{note.path}:{block_id}"
        blocks.append(
            Block(
                block_uid=uid,
                note_path=note.path,
                block_id=block_id,
                heading_path=heading_stack.copy(),
                raw_text=raw,
                clean_text=cleaned,
                char_start=block_start_char,
                char_end=current_char,
                token_count_est=max(1, len(cleaned) // 4),
                block_hash=hashlib.sha1(cleaned.encode("utf-8")).hexdigest(),
            )
        )
        seq += 1
        buffer = []
        block_start_char = current_char

    for line in lines:
        heading_match = HEADING_RE.match(line.strip())
        if heading_match:
            flush_buffer(char_cursor)
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            heading_stack = heading_stack[: level - 1] + [title]
            char_cursor += len(line)
            block_start_char = char_cursor
            continue
        if line.strip() == "":
            flush_buffer(char_cursor)
            char_cursor += len(line)
            block_start_char = char_cursor
            continue
        buffer.append(line)
        char_cursor += len(line)
    flush_buffer(char_cursor)
    return _merge_and_split(blocks, split_cfg)


def build_embedding_inputs(blocks: list[Block], cfg: BlockSplitConfig) -> list[str]:
    if not blocks:
        return []
    mode = cfg.window_mode
    if mode == "SELF":
        return [_trim_embedding_input(_with_heading(block.heading_path, block.clean_text)) for block in blocks]
    if mode == "SLIDING":
        return _build_sliding_inputs(blocks, cfg.window_neighbors)
    return [_trim_embedding_input(_with_heading(block.heading_path, block.clean_text)) for block in blocks]


def _detect_block_id(raw: str, seq: int) -> str:
    lines = raw.splitlines()
    if lines:
        match = BLOCK_ID_LINE_RE.match(lines[-1].strip())
        if match:
            return match.group(1)
    eol = BLOCK_ID_EOL_RE.search(raw)
    if eol:
        return eol.group(1)
    return f"auto-{seq:05d}"


def _merge_and_split(blocks: list[Block], cfg: BlockSplitConfig) -> list[Block]:
    if not blocks:
        return []
    merged: list[Block] = []
    for b in blocks:
        if merged and len(b.clean_text) < cfg.min_chars:
            last = merged[-1]
            combined_raw = last.raw_text + "\n" + b.raw_text
            combined_clean = clean_text(combined_raw)
            merged[-1] = replace(
                last,
                raw_text=combined_raw,
                clean_text=combined_clean,
                char_end=b.char_end,
                token_count_est=max(1, len(combined_clean) // 4),
                block_hash=hashlib.sha1(combined_clean.encode("utf-8")).hexdigest(),
            )
        else:
            merged.append(b)
    out: list[Block] = []
    for b in merged:
        if len(b.clean_text) <= cfg.max_chars:
            out.append(b)
            continue
        chunks = [b.clean_text[i : i + cfg.max_chars] for i in range(0, len(b.clean_text), cfg.max_chars)]
        for idx, chunk in enumerate(chunks):
            out.append(
                replace(
                    b,
                    block_uid=f"{b.block_uid}:part{idx}",
                    block_id=f"{b.block_id}-part{idx}",
                    clean_text=chunk,
                    token_count_est=max(1, len(chunk) // 4),
                    block_hash=hashlib.sha1(chunk.encode("utf-8")).hexdigest(),
                )
            )
    return out


def _build_sliding_inputs(blocks: list[Block], neighbors: int) -> list[str]:
    n = len(blocks)
    neighbors = max(0, neighbors)
    out: list[str] = []
    for idx, block in enumerate(blocks):
        left = max(0, idx - neighbors)
        right = min(n, idx + neighbors + 1)
        parts: list[str] = []
        heading = _format_heading(block.heading_path)
        if heading:
            parts.append(f"Heading: {heading}")
        for i in range(left, right):
            label = "Current" if i == idx else "Neighbor"
            parts.append(f"{label}: {blocks[i].clean_text}")
        out.append(_trim_embedding_input("\n".join(parts)))
    return out


def _with_heading(heading_path: list[str], text: str) -> str:
    heading = _format_heading(heading_path)
    if not heading:
        return text
    return f"Heading: {heading}\nCurrent: {text}"


def _format_heading(heading_path: list[str]) -> str:
    parts = [part.strip() for part in heading_path if part and part.strip()]
    return " > ".join(parts)


def _trim_embedding_input(text: str, max_chars: int = 2400) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
