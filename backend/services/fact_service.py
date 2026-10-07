import random
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, and_, not_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from backend.models import Fact, FactUnlock
from backend.schemas import (
    FactTeaserResponse,
    FactDetailResponse,
    FactAdminCreate,
    FactAdminUpdate,
    CategoryResponse
)
from backend.services.unlock_service import is_fact_unlocked_for_session, get_unlock_record


async def get_fact_teaser_by_id(
    db: AsyncSession,
    fact_id: int,
    session_id: Optional[str] = None
) -> Optional[FactTeaserResponse]:
    """Retrieve teaser for a specific fact."""
    stmt = select(Fact).where(and_(Fact.id == fact_id, Fact.is_active == True))
    result = await db.execute(stmt)
    fact = result.scalar_one_or_none()
    if not fact:
        return None

    is_unlocked = False
    if session_id:
        is_unlocked = await is_fact_unlocked_for_session(db, fact.id, session_id)

    return FactTeaserResponse(
        id=fact.id,
        title=fact.title,
        teaser=fact.teaser,
        category=fact.category,
        interestingness_score=fact.interestingness_score,
        is_unlocked=is_unlocked
    )


async def get_random_or_next_teaser(
    db: AsyncSession,
    session_id: Optional[str] = None,
    category: Optional[str] = None,
    exclude_id: Optional[int] = None
) -> Optional[FactTeaserResponse]:
    """
    Select an intriguing fact teaser.
    Prioritizes active, verified facts not yet unlocked by this user session.
    """
    conditions = [Fact.is_active == True, Fact.verification_status == "verified"]

    if category:
        conditions.append(Fact.category.ilike(category))

    if exclude_id:
        conditions.append(Fact.id != exclude_id)

    # If session provided, exclude facts the user has already unlocked
    if session_id:
        unlocked_subq = select(FactUnlock.fact_id).where(FactUnlock.session_id == session_id)
        # Try finding one they haven't unlocked yet
        stmt = (
            select(Fact)
            .where(and_(*conditions, not_(Fact.id.in_(unlocked_subq))))
            .order_by(desc(Fact.interestingness_score), func.random())
            .limit(1)
        )
        result = await db.execute(stmt)
        fact = result.scalar_one_or_none()
        if fact:
            return FactTeaserResponse(
                id=fact.id,
                title=fact.title,
                teaser=fact.teaser,
                category=fact.category,
                interestingness_score=fact.interestingness_score,
                is_unlocked=False
            )

    # Fallback to any random active fact
    stmt = select(Fact).where(and_(*conditions)).order_by(func.random()).limit(1)
    result = await db.execute(stmt)
    fact = result.scalar_one_or_none()
    if not fact:
        return None

    is_unlocked = False
    if session_id:
        is_unlocked = await is_fact_unlocked_for_session(db, fact.id, session_id)

    return FactTeaserResponse(
        id=fact.id,
        title=fact.title,
        teaser=fact.teaser,
        category=fact.category,
        interestingness_score=fact.interestingness_score,
        is_unlocked=is_unlocked
    )


async def get_full_fact_if_unlocked(
    db: AsyncSession,
    fact_id: int,
    session_id: str
) -> FactDetailResponse:
    """
    Security gate: Only returns full fact and explanation if the session has unlocked it.
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session identifier required to view unlocked fact."
        )

    stmt = select(Fact).where(Fact.id == fact_id)
    result = await db.execute(stmt)
    fact = result.scalar_one_or_none()
    if not fact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fact not found."
        )

    # Check unlock status
    unlock_rec = await get_unlock_record(db, fact_id, session_id)
    if not unlock_rec:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This fact is locked. Please unlock it for ₹1 to read."
        )

    return FactDetailResponse(
        id=fact.id,
        title=fact.title,
        teaser=fact.teaser,
        fact_text=fact.fact_text,
        explanation=fact.explanation,
        category=fact.category,
        source_name=fact.source_name,
        source_url=fact.source_url,
        interestingness_score=fact.interestingness_score,
        is_unlocked=True,
        unlocked_at=unlock_rec.unlocked_at
    )


async def get_all_categories_with_count(db: AsyncSession) -> List[CategoryResponse]:
    """Retrieve distinct categories with active fact counts."""
    stmt = (
        select(Fact.category, func.count(Fact.id))
        .where(Fact.is_active == True)
        .group_by(Fact.category)
        .order_by(desc(func.count(Fact.id)))
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [CategoryResponse(name=row[0], count=row[1]) for row in rows]


# Admin Service Operations
async def admin_list_facts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    search: Optional[str] = None
) -> Tuple[List[Fact], int]:
    """List facts for admin dashboard."""
    conditions = []
    if category:
        conditions.append(Fact.category.ilike(category))
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            (Fact.title.ilike(search_pattern)) | 
            (Fact.teaser.ilike(search_pattern)) |
            (Fact.fact_text.ilike(search_pattern))
        )

    count_stmt = select(func.count(Fact.id)).where(and_(*conditions)) if conditions else select(func.count(Fact.id))
    total_count = (await db.execute(count_stmt)).scalar() or 0

    stmt = select(Fact)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Fact.id.asc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all()), total_count


async def admin_create_fact(db: AsyncSession, data: FactAdminCreate) -> Fact:
    fact = Fact(
        title=data.title,
        teaser=data.teaser,
        fact_text=data.fact_text,
        explanation=data.explanation,
        category=data.category,
        source_name=data.source_name,
        source_url=data.source_url,
        interestingness_score=data.interestingness_score,
        is_active=data.is_active,
        verification_status="verified"
    )
    db.add(fact)
    await db.commit()
    await db.refresh(fact)
    return fact


async def admin_update_fact(db: AsyncSession, fact_id: int, data: FactAdminUpdate) -> Optional[Fact]:
    stmt = select(Fact).where(Fact.id == fact_id)
    result = await db.execute(stmt)
    fact = result.scalar_one_or_none()
    if not fact:
        return None

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(fact, key, value)

    await db.commit()
    await db.refresh(fact)
    return fact


async def admin_toggle_fact_active(db: AsyncSession, fact_id: int) -> Optional[Fact]:
    stmt = select(Fact).where(Fact.id == fact_id)
    result = await db.execute(stmt)
    fact = result.scalar_one_or_none()
    if not fact:
        return None

    fact.is_active = not fact.is_active
    await db.commit()
    await db.refresh(fact)
    return fact
