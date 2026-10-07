from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import FactUnlock, Order, Fact


async def is_fact_unlocked_for_session(
    db: AsyncSession,
    fact_id: int,
    session_id: str
) -> bool:
    """Check if a fact has been unlocked for a given browser session."""
    if not session_id or not fact_id:
        return False

    stmt = select(FactUnlock).where(
        and_(
            FactUnlock.fact_id == fact_id,
            FactUnlock.session_id == session_id
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_unlock_record(
    db: AsyncSession,
    fact_id: int,
    session_id: str
) -> Optional[FactUnlock]:
    """Retrieve the unlock record for a fact and session."""
    stmt = select(FactUnlock).where(
        and_(
            FactUnlock.fact_id == fact_id,
            FactUnlock.session_id == session_id
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def record_fact_unlock(
    db: AsyncSession,
    order_id: str,
    fact_id: int,
    session_id: str
) -> FactUnlock:
    """Create a new unlock record linked to a verified order."""
    # Check if already unlocked to prevent duplicates
    existing = await get_unlock_record(db, fact_id, session_id)
    if existing:
        return existing

    unlock = FactUnlock(
        order_id=order_id,
        fact_id=fact_id,
        session_id=session_id,
        unlocked_at=datetime.now(timezone.utc)
    )
    db.add(unlock)
    await db.flush()
    return unlock


async def get_all_unlocked_facts_for_session(
    db: AsyncSession,
    session_id: str
) -> List[Fact]:
    """Retrieve all facts unlocked by this session."""
    stmt = (
        select(Fact)
        .join(FactUnlock, Fact.id == FactUnlock.fact_id)
        .where(FactUnlock.session_id == session_id)
        .order_by(FactUnlock.unlocked_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
