from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas import QueryBlockRequest, QueryNoteRequest, QuerySearchRequest

router = APIRouter(prefix="/v1/query", tags=["query"])


@router.post("/note")
def query_note(payload: QueryNoteRequest, request: Request) -> dict:
    container = request.app.state.container
    return container.query_service.query_note(
        note_path=payload.note_path,
        top_k=payload.top_k,
        threshold=payload.threshold,
    )


@router.post("/block")
def query_block(payload: QueryBlockRequest, request: Request) -> dict:
    container = request.app.state.container
    return container.query_service.query_block(payload.block_uid, payload.top_k)


@router.post("/search")
def search(payload: QuerySearchRequest, request: Request) -> dict:
    container = request.app.state.container
    return container.query_service.search(payload.text, payload.top_k, payload.threshold)
