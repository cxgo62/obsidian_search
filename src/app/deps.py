from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from app.container import AppContainer


def get_container(request: Request) -> AppContainer:
    return request.app.state.container  # type: ignore[no-any-return]


def require_token(request: Request, x_api_token: str | None = Header(default=None)) -> None:
    container = get_container(request)
    expected = container.settings.api_token
    if not expected:
        return
    if x_api_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
