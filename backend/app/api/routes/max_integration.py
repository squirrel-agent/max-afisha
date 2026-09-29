from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cities import is_supported_city
from app.core.config import settings
from app.core.max_auth import MaxInitDataError, validate_max_init_data
from app.db.session import get_db
from app.models.user import User, UserPreference

router = APIRouter(prefix="/max", tags=["max"])


class MaxSessionPayload(BaseModel):
    init_data: str = Field(min_length=1, max_length=20_000)
    city: str = "moscow"


@router.post("/session")
async def max_session(
    payload: MaxSessionPayload,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.max_bot_token:
        raise HTTPException(status_code=503, detail="MAX integration is not configured")
    if not is_supported_city(payload.city):
        raise HTTPException(status_code=400, detail=f"Unsupported city: {payload.city}")

    try:
        max_user = validate_max_init_data(
            payload.init_data,
            settings.max_bot_token,
            max_age_seconds=settings.max_init_data_max_age_seconds,
        )
    except MaxInitDataError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    max_user_id = int(max_user["id"])
    result = await db.execute(select(User).where(User.max_user_id == max_user_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(max_user_id=max_user_id, city=payload.city)
        db.add(user)
        await db.flush()
        db.add(UserPreference(user_id=user.id))
    else:
        user.city = payload.city
        if await db.get(UserPreference, user.id) is None:
            db.add(UserPreference(user_id=user.id))

    await db.commit()
    return {
        "id": user.id,
        "city": user.city,
        "max_user_id": max_user_id,
        "authenticated_via": "max_init_data",
    }
