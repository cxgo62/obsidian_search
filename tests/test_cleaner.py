from __future__ import annotations

from indexing.cleaner import clean_text


def test_clean_text_strips_link_urls_and_keeps_anchor_text() -> None:
    raw = "see [scrum](https://example.com/http/api/path) and https://foo.bar/api/v1 with [[Target|显示名]]"
    cleaned = clean_text(raw)
    assert "https://" not in cleaned
    assert "http" not in cleaned.lower()
    assert "api/path" not in cleaned.lower()
    assert "scrum" in cleaned
    assert "显示名" in cleaned
