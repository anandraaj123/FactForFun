import json
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import AnalyticsEvent


async def record_event(
    db: AsyncSession,
    event_type: str,
    session_id: Optional[str] = None,
    fact_id: Optional[int] = None,
    meta: Optional[Dict[str, Any]] = None
) -> AnalyticsEvent:
    """Record an anonymous product interaction event."""
    meta_json_str = json.dumps(meta) if meta else None
    
    event = AnalyticsEvent(
        event_type=event_type,
        session_id=session_id,
        fact_id=fact_id,
        meta_json=meta_json_str
    )
    db.add(event)
    await db.commit()
    return event
