from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from app.core.config import settings


def require_admin(authorization: str | None = Header(default=None)) -> None:
    """Protect mutating/expensive operational endpoints with ADMIN_TOKEN."""
    expected = f"Bearer {settings.admin_token}"
    if (
        not settings.admin_token
        or not authorization
        or not hmac.compare_digest(authorization, expected)
    ):
        raise HTTPException(status_code=401, detail="Invalid admin token")
