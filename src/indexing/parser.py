from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import frontmatter

from app.models import LinkRef, NoteDoc

WIKILINK_RE = re.compile(r"(!)?\[\[([^\]]+)\]\]")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def parse_markdown_file(path: Path, vault_path: Path) -> NoteDoc:
    text = path.read_text(encoding="utf-8")
    post = frontmatter.loads(text)
    body = post.content
    rel_path = str(path.relative_to(vault_path))
    front = dict(post.metadata)
    aliases = _as_string_list(front.get("aliases", []))
    tags = _extract_tags(front, body)
    links = extract_links(rel_path, body)
    return NoteDoc(
        path=rel_path,
        title=path.stem,
        aliases=aliases,
        tags=tags,
        frontmatter=front,
        body=body,
        content_hash=hashlib.sha1(text.encode("utf-8")).hexdigest(),
        mtime=path.stat().st_mtime,
        links=links,
    )


def extract_links(note_path: str, body: str) -> list[LinkRef]:
    links: list[LinkRef] = []
    for match in WIKILINK_RE.finditer(body):
        is_embed = bool(match.group(1))
        content = match.group(2).strip()
        if "|" in content:
            target, link_text = content.split("|", 1)
            link_text = link_text.strip()
        else:
            target, link_text = content, None
        dst_note, dst_heading, dst_block_id = _parse_target(target.strip())
        links.append(
            LinkRef(
                src_note_path=note_path,
                src_block_uid=None,
                dst_note_path=dst_note,
                dst_heading=dst_heading,
                dst_block_id=dst_block_id,
                link_text=link_text,
                link_type="embed" if is_embed else "wikilink",
            )
        )
    for match in MD_LINK_RE.finditer(body):
        label, href = match.group(1).strip(), match.group(2).strip()
        if href.startswith("http://") or href.startswith("https://"):
            continue
        dst_note, dst_heading, dst_block_id = _parse_target(href)
        links.append(
            LinkRef(
                src_note_path=note_path,
                src_block_uid=None,
                dst_note_path=dst_note,
                dst_heading=dst_heading,
                dst_block_id=dst_block_id,
                link_text=label,
                link_type="mdlink",
            )
        )
    return links


def _parse_target(raw: str) -> tuple[str, str | None, str | None]:
    dst_heading = None
    dst_block = None
    target = raw
    if "#^" in raw:
        target, dst_block = raw.split("#^", 1)
    elif "#" in raw:
        target, dst_heading = raw.split("#", 1)
    target = target.strip() or ""
    return target if target.endswith(".md") else f"{target}.md", dst_heading, dst_block


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _extract_tags(frontmatter_data: dict[str, Any], body: str) -> list[str]:
    tags = set(_as_string_list(frontmatter_data.get("tags", [])))
    inline_tags = re.findall(r"(?<!\w)#([a-zA-Z0-9_\-/]+)", body)
    tags.update(inline_tags)
    return sorted(tags)
