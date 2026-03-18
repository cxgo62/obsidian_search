from __future__ import annotations

import re

WIKILINK_DISPLAY_RE = re.compile(r"\[\[([^|\]]+)\|([^\]]+)\]\]")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.S)
MD_LINK_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)")
URL_RE = re.compile(r"https?://[^\s)>]+")


def clean_text(raw: str) -> str:
    text = HTML_COMMENT_RE.sub(" ", raw)
    text = WIKILINK_DISPLAY_RE.sub(r"\2", text)
    text = WIKILINK_RE.sub(lambda m: m.group(1).split("|", 1)[0], text)
    text = MD_LINK_RE.sub(lambda m: (m.group(1) or m.group(3) or " ").strip() or " ", text)
    text = URL_RE.sub(" ", text)
    text = re.sub(r"`{3}[\s\S]*?`{3}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
