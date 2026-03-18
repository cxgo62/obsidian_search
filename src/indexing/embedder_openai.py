from __future__ import annotations

import hashlib
import logging
import math
from collections.abc import Iterable

try:
    import tiktoken
except Exception:  # pragma: no cover
    tiktoken = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

logger = logging.getLogger("obsidian_search.embedder")


class OpenAIEmbedder:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        dimensions: int | None,
        base_url: str | None = None,
        batch_size: int = 128,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size
        kwargs: dict[str, str] = {}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(api_key=api_key, **kwargs) if (OpenAI and api_key) else None
        self._encoding = tiktoken.get_encoding("cl100k_base") if tiktoken else None

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        values = [t for t in texts if t.strip()]
        if not values:
            return []
        if self._client is None:
            return [_pseudo_embedding(t, self._dimensions or 256) for t in values]
        try:
            vectors: list[list[float]] = []
            for batch in _batch_by_count(values, self._batch_size):
                kwargs = {"model": self._model, "input": batch}
                if self._dimensions is not None:
                    kwargs["dimensions"] = self._dimensions
                resp = self._client.embeddings.create(**kwargs)
                vectors.extend([list(item.embedding) for item in resp.data])
            return vectors
        except Exception as exc:  # pragma: no cover - network/quota/runtime dependent
            logger.warning("embedding upstream failed, fallback to pseudo embedding: %s", exc)
            return [_pseudo_embedding(t, self._dimensions or 256) for t in values]

    def estimate_tokens(self, text: str) -> int:
        if self._encoding is None:
            return max(1, len(text) // 4)
        return len(self._encoding.encode(text))


def _batch_by_count(values: list[str], size: int) -> list[list[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def _pseudo_embedding(text: str, dims: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for i in range(dims):
        b = digest[i % len(digest)]
        values.append((b / 255.0) - 0.5)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]
