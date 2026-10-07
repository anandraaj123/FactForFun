from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models import Fact, Order, FactUnlock
from backend.schemas import (
    FactDetailResponse,
    FactAdminCreate,
    FactAdminUpdate,
    AdminStatsResponse
)
from backend.security import get_admin_auth
from backend.services.fact_service import (
    admin_list_facts,
    admin_create_fact,
    admin_update_fact,
    admin_toggle_fact_active
)

router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(get_admin_auth)])


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Retrieve operational statistics: revenue, payments, active facts, popular categories."""
    total_facts = (await db.execute(select(func.count(Fact.id)))).scalar() or 0
    active_facts = (await db.execute(select(func.count(Fact.id)).where(Fact.is_active == True))).scalar() or 0
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    successful_orders = (await db.execute(select(func.count(Order.id)).where(Order.status == "paid"))).scalar() or 0
    total_revenue_paise = (await db.execute(select(func.sum(Order.amount)).where(Order.status == "paid"))).scalar() or 0
    total_unlocks = (await db.execute(select(func.count(FactUnlock.id)))).scalar() or 0

    # Category breakdown
    cat_stmt = (
        select(Fact.category, func.count(FactUnlock.id).label("unlock_count"))
        .join(FactUnlock, Fact.id == FactUnlock.fact_id, isouter=True)
        .group_by(Fact.category)
        .order_by(desc("unlock_count"))
        .limit(10)
    )
    cat_res = await db.execute(cat_stmt)
    popular_categories = [{"category": row[0], "unlocks": row[1]} for row in cat_res.all()]

    # Recent unlocks
    recent_stmt = (
        select(FactUnlock.unlocked_at, Fact.title, Fact.category, FactUnlock.order_id)
        .join(Fact, Fact.id == FactUnlock.fact_id)
        .order_by(FactUnlock.unlocked_at.desc())
        .limit(10)
    )
    recent_res = await db.execute(recent_stmt)
    recent_unlocks = [
        {
            "unlocked_at": row[0].isoformat() if row[0] else None,
            "title": row[1],
            "category": row[2],
            "order_id": row[3]
        }
        for row in recent_res.all()
    ]

    return AdminStatsResponse(
        total_facts=total_facts,
        active_facts=active_facts,
        total_orders=total_orders,
        successful_orders=successful_orders,
        total_revenue_inr=total_revenue_paise / 100.0,
        total_unlocks=total_unlocks,
        popular_categories=popular_categories,
        recent_unlocks=recent_unlocks
    )


@router.get("/facts")
async def list_facts_for_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List facts with pagination, category filter, and search."""
    facts, total = await admin_list_facts(
        db=db,
        skip=skip,
        limit=limit,
        category=category,
        search=search
    )
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "facts": facts
    }


@router.post("/facts", response_model=FactDetailResponse)
async def create_new_fact(
    data: FactAdminCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a new verified fact to the database."""
    fact = await admin_create_fact(db=db, data=data)
    return fact


@router.put("/facts/{fact_id}", response_model=FactDetailResponse)
async def update_fact(
    fact_id: int,
    data: FactAdminUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update details of an existing fact."""
    fact = await admin_update_fact(db=db, fact_id=fact_id, data=data)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return fact


@router.patch("/facts/{fact_id}/toggle-active")
async def toggle_fact_active_status(
    fact_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Toggle active status of a fact."""
    fact = await admin_toggle_fact_active(db=db, fact_id=fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return {"id": fact.id, "is_active": fact.is_active}
