from fastapi import APIRouter

from app.cities import CITIES

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("")
async def list_cities() -> list[dict[str, object]]:
    return CITIES
