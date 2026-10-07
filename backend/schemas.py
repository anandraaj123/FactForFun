from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class FactTeaserResponse(BaseModel):
    id: int
    title: str
    teaser: str
    category: str
    interestingness_score: int
    is_unlocked: bool = False

    model_config = {"from_attributes": True}


class FactDetailResponse(BaseModel):
    id: int
    title: str
    teaser: str
    fact_text: str
    explanation: str
    category: str
    source_name: str
    source_url: str
    interestingness_score: int
    is_unlocked: bool = True
    unlocked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CategoryResponse(BaseModel):
    name: str
    count: int


class CreateOrderRequest(BaseModel):
    fact_id: Optional[int] = None
    session_id: str = Field(..., min_length=8, max_length=128)


class CreateOrderResponse(BaseModel):
    order_id: str
    fact_id: int
    amount: int  # in paise
    amount_inr: float
    currency: str
    gateway_name: str
    gateway_key_id: Optional[str] = None
    gateway_order_id: Optional[str] = None
    payment_session_id: Optional[str] = None  # Cashfree Web SDK payment_session_id
    cashfree_env: Optional[str] = None       # 'sandbox' or 'production'
    status: str


class VerifyPaymentRequest(BaseModel):
    order_id: str
    gateway_order_id: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    gateway_signature: Optional[str] = None
    session_id: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    fact_id: int
    order_id: str
    fact: Optional[FactDetailResponse] = None


class FactAdminCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    teaser: str = Field(..., min_length=10)
    fact_text: str = Field(..., min_length=10)
    explanation: str = Field(..., min_length=10)
    category: str = Field(..., min_length=2, max_length=64)
    source_name: str = Field(..., min_length=2, max_length=255)
    source_url: str = Field(..., min_length=5, max_length=1024)
    interestingness_score: int = Field(5, ge=1, le=5)
    is_active: bool = True


class FactAdminUpdate(BaseModel):
    title: Optional[str] = None
    teaser: Optional[str] = None
    fact_text: Optional[str] = None
    explanation: Optional[str] = None
    category: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    interestingness_score: Optional[int] = Field(None, ge=1, le=5)
    is_active: Optional[bool] = None
    verification_status: Optional[str] = None


class AdminStatsResponse(BaseModel):
    total_facts: int
    active_facts: int
    total_orders: int
    successful_orders: int
    total_revenue_inr: float
    total_unlocks: int
    popular_categories: List[Dict[str, Any]]
    recent_unlocks: List[Dict[str, Any]]


class AnalyticsEventRequest(BaseModel):
    event_type: str = Field(..., min_length=2, max_length=64)
    session_id: Optional[str] = None
    fact_id: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None
