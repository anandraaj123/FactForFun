from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Fact(Base):
    __tablename__ = "facts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    teaser = Column(Text, nullable=False)
    fact_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    category = Column(String(64), nullable=False, index=True)
    source_name = Column(String(255), nullable=False)
    source_url = Column(String(1024), nullable=False)
    interestingness_score = Column(Integer, default=5)
    verification_status = Column(String(32), default="verified", index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    orders = relationship("Order", back_populates="fact", cascade="all, delete-orphan")
    unlocks = relationship("FactUnlock", back_populates="fact", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(String(128), unique=True, index=True, nullable=False)  # Internal UUID
    session_id = Column(String(128), index=True, nullable=False)
    fact_id = Column(Integer, ForeignKey("facts.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)  # in paise (100 paise = ₹1)
    currency = Column(String(8), default="INR")
    status = Column(String(32), default="created", index=True)  # created, paid, failed, expired
    
    # Gateway specific
    gateway_name = Column(String(32), default="simulator")  # razorpay, simulator
    gateway_order_id = Column(String(128), nullable=True, index=True)
    gateway_payment_id = Column(String(128), nullable=True, index=True)
    gateway_signature = Column(String(256), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    fact = relationship("Fact", back_populates="orders")
    unlock = relationship("FactUnlock", back_populates="order", uselist=False)


class FactUnlock(Base):
    __tablename__ = "fact_unlocks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(String(128), ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, unique=True)
    fact_id = Column(Integer, ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(128), index=True, nullable=False)
    unlocked_at = Column(DateTime(timezone=True), default=utc_now)

    # Compound index for session + fact queries
    __table_args__ = (
        Index("ix_fact_unlocks_session_fact", "session_id", "fact_id"),
    )

    # Relationships
    order = relationship("Order", back_populates="unlock")
    fact = relationship("Fact", back_populates="unlocks")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String(64), index=True, nullable=False)  # page_view, teaser_view, unlock_clicked, payment_started, payment_success, fact_shared
    session_id = Column(String(128), index=True, nullable=True)
    fact_id = Column(Integer, nullable=True)
    meta_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
