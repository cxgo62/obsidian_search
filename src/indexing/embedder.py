from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


class Embedder(Protocol):
    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        ...

    def estimate_tokens(self, text: str) -> int:
        ...
