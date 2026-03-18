from __future__ import annotations

from pydantic import BaseModel, Field


class IndexFileRequest(BaseModel):
    note_path: str


class QueryNoteRequest(BaseModel):
    note_path: str
    top_k: int | None = Field(default=None, ge=1, le=100)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class QueryBlockRequest(BaseModel):
    block_uid: str
    top_k: int | None = Field(default=None, ge=1, le=100)


class QuerySearchRequest(BaseModel):
    text: str
    top_k: int | None = Field(default=None, ge=1, le=200)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
