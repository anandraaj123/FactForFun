from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.schemas import AnalyticsEventRequest
from backend.services.analytics_service import record_event

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.post("/event")
async def track_funnel_event(
    event: AnalyticsEventRequest,
    db: AsyncSession = Depends(get_db)
):
    """Record an anonymous product event (e.g. teaser_view, unlock_clicked, fact_shared)."""
    await record_event(
        db=db,
        event_type=event.event_type,
        session_id=event.session_id,
        fact_id=event.fact_id,
        meta=event.meta
    )
    return {"status": "ok"}
