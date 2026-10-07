import json
from fastapi import APIRouter, Depends, Request, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.config import settings
from backend.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse
)
from backend.models import Order
from backend.services.payment_service import (
    create_payment_order,
    verify_and_unlock_payment,
    process_cashfree_webhook,
    process_razorpay_webhook
)
from backend.security import (
    verify_cashfree_webhook_signature,
    verify_razorpay_webhook_signature
)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.post("/create", response_model=CreateOrderResponse)
async def create_order(
    request_data: CreateOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a ₹1 order to unlock a fact.
    Returns the order ID, payment_session_id, and gateway configuration.
    """
    return await create_payment_order(db=db, data=request_data)


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    request_data: VerifyPaymentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Server-side verification of payment authenticity.
    Once verified, the fact is permanently unlocked for this session.
    """
    return await verify_and_unlock_payment(db=db, data=request_data)


@router.post("/cashfree-webhook")
async def cashfree_webhook(
    request: Request,
    x_webhook_signature: str = Header(None),
    x_webhook_timestamp: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Cashfree PG Webhook endpoint for asynchronous payment updates.
    Verifies x-webhook-signature header against timestamp and body.
    """
    body_bytes = await request.body()

    if settings.PAYMENT_MODE.lower() == "cashfree" and settings.CASHFREE_SECRET_KEY != "placeholder_cashfree_secret_key":
        if not x_webhook_signature or not x_webhook_timestamp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Cashfree webhook signature or timestamp header"
            )
        is_valid = verify_cashfree_webhook_signature(
            timestamp=x_webhook_timestamp,
            raw_body=body_bytes,
            received_signature=x_webhook_signature,
            secret_key=settings.CASHFREE_SECRET_KEY
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Cashfree webhook signature"
            )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    await process_cashfree_webhook(db=db, payload=payload)
    return {"status": "ok"}


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Razorpay Webhook endpoint for asynchronous payment updates.
    """
    body_bytes = await request.body()
    
    if settings.PAYMENT_MODE.lower() == "razorpay" and settings.PAYMENT_WEBHOOK_SECRET != "placeholder_webhook_secret":
        if not x_razorpay_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Razorpay-Signature header"
            )
        is_valid = verify_razorpay_webhook_signature(
            raw_body=body_bytes,
            received_signature=x_razorpay_signature,
            webhook_secret=settings.PAYMENT_WEBHOOK_SECRET
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
            
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    await process_razorpay_webhook(db=db, payload=payload)
    return {"status": "ok"}


@router.get("/status/{order_id}")
async def check_order_status(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Check payment status for an order."""
    stmt = select(Order).where(Order.order_id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    return {
        "order_id": order.order_id,
        "fact_id": order.fact_id,
        "amount": order.amount,
        "currency": order.currency,
        "status": order.status,
        "gateway_name": order.gateway_name
    }
