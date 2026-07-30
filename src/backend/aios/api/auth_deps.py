"""FastAPI dependency for auth verification."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from aios.core.auth import AuthManager


async def verify_auth(request: Request) -> None:
    """FastAPI dependency that verifies the Authorization header."""
    auth_manager: AuthManager = request.app.state.auth_manager
    auth_header = request.headers.get("Authorization")
    if not auth_manager.verify(auth_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


# Dependency for routes that should be publicly accessible
async def no_auth() -> None:
    pass
