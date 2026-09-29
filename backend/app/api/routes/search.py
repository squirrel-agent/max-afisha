from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.search import NeuralSearchRequest, NeuralSearchResponse
from app.services.neural_search import neural_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/neural", response_model=NeuralSearchResponse)
async def run_neural_search(
    payload: NeuralSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        return await neural_search(db, payload)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Neural search failed: {type(exc).__name__}: {exc}",
        ) from exc
