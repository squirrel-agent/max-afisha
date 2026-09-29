from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class MaxInitDataError(ValueError):
    pass


def validate_max_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 3600,
    now: int | None = None,
) -> dict:
    """Validate signed MAX Mini App initData and return the MAX user payload.

    The signature is checked before any user-provided identity is trusted.
    Duplicate keys are rejected so canonicalization cannot be ambiguous.
    """
    if not bot_token:
        raise MaxInitDataError("MAX bot token is not configured")
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise MaxInitDataError("Malformed MAX init data") from exc
    if not pairs:
        raise MaxInitDataError("Empty MAX init data")

    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise MaxInitDataError("Duplicate keys in MAX init data")

    data = dict(pairs)
    supplied_hash = data.pop("hash", None)
    if not supplied_hash:
        raise MaxInitDataError("MAX init data has no hash")

    data_check_string = "\n".join(f"{key}={data[key]}" for key in sorted(data))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, supplied_hash):
        raise MaxInitDataError("Invalid MAX init data signature")

    try:
        auth_date = int(data["auth_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MaxInitDataError("MAX init data has invalid auth_date") from exc

    current = int(time.time() if now is None else now)
    if auth_date > current + 300:
        raise MaxInitDataError("MAX init data auth_date is in the future")
    if current - auth_date > max_age_seconds:
        raise MaxInitDataError("MAX init data has expired")

    raw_user = data.get("user")
    if not raw_user:
        raise MaxInitDataError("MAX init data has no user")
    try:
        user = json.loads(raw_user)
        user_id = int(user["id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise MaxInitDataError("MAX init data has invalid user payload") from exc
    if user_id <= 0:
        raise MaxInitDataError("MAX user id must be positive")
    return user
