from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.schemas import (
    FactTeaserResponse,
    FactDetailResponse,
    CategoryResponse
)
from backend.services.fact_service import (
    get_random_or_next_teaser,
    get_fact_teaser_by_id,
    get_full_fact_if_unlocked,
    get_all_categories_with_count
)
from backend.services.unlock_service import get_all_unlocked_facts_for_session

router = APIRouter(prefix="/api/facts", tags=["Facts"])


@router.get("/teaser", response_model=FactTeaserResponse)
async def get_teaser(
    session_id: Optional[str] = Query(None, description="Client session ID to avoid showing already unlocked facts"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    exclude_id: Optional[int] = Query(None, description="Exclude a specific fact ID from the random pool"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get an intriguing fact teaser.
    Returns only the question/teaser and category. Full fact text remains hidden.
    """
    teaser = await get_random_or_next_teaser(
        db=db,
        session_id=session_id,
        category=category,
        exclude_id=exclude_id
    )
    if not teaser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No facts available matching the criteria."
        )
    return teaser


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all categories with count of active facts."""
    return await get_all_categories_with_count(db)


@router.get("/{fact_id}/teaser", response_model=FactTeaserResponse)
async def get_specific_teaser(
    fact_id: int,
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get the teaser of a specific fact by ID."""
    teaser = await get_fact_teaser_by_id(db=db, fact_id=fact_id, session_id=session_id)
    if not teaser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fact not found."
        )
    return teaser


@router.get("/{fact_id}", response_model=FactDetailResponse)
async def get_unlocked_fact(
    fact_id: int,
    session_id: str = Query(..., description="Active browser session ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch the unlocked full fact, explanation, and verified source.
    Requires server-verified payment / unlock for this session.
    """
    return await get_full_fact_if_unlocked(db=db, fact_id=fact_id, session_id=session_id)


@router.get("/unlocked/history", response_model=List[FactDetailResponse])
async def get_unlocked_history(
    session_id: str = Query(..., description="Active browser session ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch all facts unlocked by the current session (user's curiosity collection).
    """
    unlocked_facts = await get_all_unlocked_facts_for_session(db=db, session_id=session_id)
    return [
        FactDetailResponse(
            id=f.id,
            title=f.title,
            teaser=f.teaser,
            fact_text=f.fact_text,
            explanation=f.explanation,
            category=f.category,
            source_name=f.source_name,
            source_url=f.source_url,
            interestingness_score=f.interestingness_score,
            is_unlocked=True,
            unlocked_at=None
        )
        for f in unlocked_facts
    ]
