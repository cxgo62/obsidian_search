from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["ui"])


@router.get("/")
def home() -> FileResponse:
    root = Path(__file__).resolve().parents[3]
    page = root / "web" / "index.html"
    return FileResponse(page)
