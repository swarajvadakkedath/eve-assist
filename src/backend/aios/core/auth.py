"""Authentication middleware for all API endpoints."""

from __future__ import annotations

import os
import secrets
from typing import Set

import structlog

logger = structlog.get_logger(__name__)


class AuthManager:
    """Manages API authentication token.
    
    The token is auto-generated at startup and exposed to the frontend.
    All API calls must include Authorization: Bearer <token> header.
    """

    def __init__(self):
        self._token: str | None = None
        self._token_set: Set[str] = set()

    @property
    def token(self) -> str:
        if self._token is None:
            self._token = os.environ.get("EVE_API_TOKEN") or secrets.token_urlsafe(32)
            self._token_set = {self._token}
        return self._token

    def verify(self, auth_header: str | None) -> bool:
        if not auth_header:
            return False
        if not auth_header.startswith("Bearer "):
            return False
        token = auth_header[7:]
        return token in self._token_set
