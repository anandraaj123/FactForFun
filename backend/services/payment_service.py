import uuid
import hmac
import hashlib
import requests
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, and_, not_, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from backend.config import settings
from backend.models import Order, Fact, FactUnlock
from backend.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
    FactDetailResponse
)
from backend.security import verify_razorpay_payment_signature
from backend.services.unlock_service import record_fact_unlock, get_unlock_record

try:
    import razorpay
    razorpay_client = razorpay.Client(auth=(settings.PAYMENT_KEY_ID, settings.PAYMENT_KEY_SECRET))
except Exception:
    razorpay_client = None


def get_cashfree_base_url() -> str:
    """Return Cashfree PG Base API URL depending on environment."""
    if settings.CASHFREE_ENV.lower() == "production":
        return "https://api.cashfree.com/pg"
    return "https://sandbox.cashfree.com/pg"


async def create_payment_order(
    db: AsyncSession,
    data: CreateOrderRequest
) -> CreateOrderResponse:
    """
    Create a ₹1 payment order for a fact.
    Supports Cashfree Payments PG (Standard), Razorpay, and Simulator Mode.
    """
    # 1. Select fact (either specified or random unread fact)
    if data.fact_id:
        stmt = select(Fact).where(and_(Fact.id == data.fact_id, Fact.is_active == True))
        result = await db.execute(stmt)
        fact = result.scalar_one_or_none()
        if not fact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fact not found or unavailable."
            )

        already_unlocked = await get_unlock_record(db, fact.id, data.session_id)
        if already_unlocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fact is already unlocked for this session."
            )
    else:
        # Pick a random unread fact for this session
        unlocked_subq = select(FactUnlock.fact_id).where(FactUnlock.session_id == data.session_id)
        stmt = (
            select(Fact)
            .where(and_(Fact.is_active == True, Fact.verification_status == "verified", not_(Fact.id.in_(unlocked_subq))))
            .order_by(func.random())
            .limit(1)
        )
        result = await db.execute(stmt)
        fact = result.scalar_one_or_none()
        if not fact:
            stmt_all = select(Fact).where(Fact.is_active == True).order_by(func.random()).limit(1)
            fact = (await db.execute(stmt_all)).scalar_one_or_none()
            if not fact:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No facts available."
                )

    # 2. Setup internal Order Details
    internal_order_id = f"fact_ord_{uuid.uuid4().hex[:14]}"
    amount_paise = settings.DEFAULT_FACT_PRICE_PAISE  # 100 paise = ₹1.00
    amount_inr = amount_paise / 100.0
    currency = settings.CURRENCY

    gateway_order_id = None
    payment_session_id = None
    gateway_name = settings.PAYMENT_MODE.lower()

    # 3. Gateway Integration
    if gateway_name == "cashfree" and settings.CASHFREE_APP_ID != "placeholder_cashfree_app_id":
        try:
            cf_url = f"{get_cashfree_base_url()}/orders"
            cf_headers = {
                "x-client-id": settings.CASHFREE_APP_ID,
                "x-client-secret": settings.CASHFREE_SECRET_KEY,
                "x-api-version": settings.CASHFREE_API_VERSION,
                "Content-Type": "application/json"
            }
            # Customer ID clean formatting
            clean_cust_id = f"cust_{data.session_id.replace('sess_', '')[:20]}"
            cf_payload = {
                "order_id": internal_order_id,
                "order_amount": amount_inr,
                "order_currency": currency,
                "customer_details": {
                    "customer_id": clean_cust_id,
                    "customer_phone": "9999999999",
                    "customer_name": "Fact1 Reader"
                },
                "order_meta": {
                    "return_url": f"{settings.FRONTEND_URL}/?order_id={internal_order_id}"
                },
                "order_note": f"Fact ₹1 Curiosity #{fact.id}"
            }
            
            response = requests.post(cf_url, json=cf_payload, headers=cf_headers, timeout=10)
            if response.status_code not in [200, 201]:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Cashfree order creation error: {response.text}"
                )
            
            cf_data = response.json()
            gateway_order_id = cf_data.get("cf_order_id") or cf_data.get("order_id")
            payment_session_id = cf_data.get("payment_session_id")
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cashfree service unavailable: {str(e)}"
            )

    elif gateway_name == "razorpay" and settings.PAYMENT_KEY_ID != "rzp_test_placeholder_key_id":
        try:
            rzp_order_payload = {
                "amount": amount_paise,
                "currency": currency,
                "receipt": internal_order_id,
                "notes": {
                    "fact_id": str(fact.id),
                    "session_id": data.session_id
                }
            }
            rzp_order = razorpay_client.order.create(data=rzp_order_payload)
            gateway_order_id = rzp_order.get("id")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Razorpay error: {str(e)}"
            )
    else:
        # Built-in simulator for instant testing
        gateway_name = "simulator"
        gateway_order_id = f"sim_ord_{uuid.uuid4().hex[:12]}"
        payment_session_id = f"sim_session_{uuid.uuid4().hex[:12]}"

    # 4. Save order in Database
    order = Order(
        order_id=internal_order_id,
        session_id=data.session_id,
        fact_id=fact.id,
        amount=amount_paise,
        currency=currency,
        status="created",
        gateway_name=gateway_name,
        gateway_order_id=str(gateway_order_id) if gateway_order_id else None
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    return CreateOrderResponse(
        order_id=order.order_id,
        fact_id=fact.id,
        amount=order.amount,
        amount_inr=amount_inr,
        currency=order.currency,
        gateway_name=gateway_name,
        gateway_key_id=settings.CASHFREE_APP_ID if gateway_name == "cashfree" else (settings.PAYMENT_KEY_ID if gateway_name == "razorpay" else "sim_key"),
        gateway_order_id=order.gateway_order_id,
        payment_session_id=payment_session_id,
        cashfree_env=settings.CASHFREE_ENV.lower(),
        status=order.status
    )


async def verify_and_unlock_payment(
    db: AsyncSession,
    data: VerifyPaymentRequest
) -> VerifyPaymentResponse:
    """
    Verify payment authenticity server-side and unlock the fact.
    Ensures that clients cannot fake payments.
    """
    # 1. Fetch internal order
    stmt = select(Order).where(Order.order_id == data.order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    # 2. Session check
    if order.session_id != data.session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session mismatch for this order."
        )

    # 3. If already paid, return fact (idempotent)
    if order.status == "paid":
        fact_stmt = select(Fact).where(Fact.id == order.fact_id)
        fact_res = await db.execute(fact_stmt)
        fact = fact_res.scalar_one_or_none()
        unlock_rec = await get_unlock_record(db, order.fact_id, order.session_id)
        
        return VerifyPaymentResponse(
            success=True,
            message="Payment already verified.",
            fact_id=order.fact_id,
            order_id=order.order_id,
            fact=FactDetailResponse(
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
                unlocked_at=unlock_rec.unlocked_at if unlock_rec else None
            )
        )

    # 4. Gateway Verification
    if order.gateway_name == "cashfree":
        # Verify status directly with Cashfree PG Servers
        cf_url = f"{get_cashfree_base_url()}/orders/{order.order_id}"
        cf_headers = {
            "x-client-id": settings.CASHFREE_APP_ID,
            "x-client-secret": settings.CASHFREE_SECRET_KEY,
            "x-api-version": settings.CASHFREE_API_VERSION
        }
        try:
            cf_res = requests.get(cf_url, headers=cf_headers, timeout=10)
            if cf_res.status_code == 200:
                cf_data = cf_res.json()
                if cf_data.get("order_status") != "PAID":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cashfree order is not paid yet (Status: {cf_data.get('order_status')})"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not verify order with Cashfree"
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Cashfree verification error: {str(e)}"
            )

    elif order.gateway_name == "razorpay":
        if not data.gateway_order_id or not data.gateway_payment_id or not data.gateway_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing payment gateway verification parameters."
            )
        
        is_valid = verify_razorpay_payment_signature(
            razorpay_order_id=data.gateway_order_id,
            razorpay_payment_id=data.gateway_payment_id,
            razorpay_signature=data.gateway_signature,
            secret=settings.PAYMENT_KEY_SECRET
        )
        if not is_valid:
            order.status = "failed"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment signature verification failed."
            )
    else:
        # Simulator verification for local testing
        if not data.gateway_payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment ID required."
            )

    # 5. Atomic Update: Mark Order Paid + Record Fact Unlock
    order.status = "paid"
    order.gateway_payment_id = data.gateway_payment_id or "cf_paid"
    order.gateway_signature = data.gateway_signature

    unlock = await record_fact_unlock(
        db=db,
        order_id=order.order_id,
        fact_id=order.fact_id,
        session_id=order.session_id
    )

    await db.commit()
    await db.refresh(order)

    # 6. Return Unlocked Fact
    fact_stmt = select(Fact).where(Fact.id == order.fact_id)
    fact_res = await db.execute(fact_stmt)
    fact = fact_res.scalar_one_or_none()

    return VerifyPaymentResponse(
        success=True,
        message="Payment verified successfully. Curiosity unlocked!",
        fact_id=fact.id,
        order_id=order.order_id,
        fact=FactDetailResponse(
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
            unlocked_at=unlock.unlocked_at
        )
    )


async def process_cashfree_webhook(
    db: AsyncSession,
    payload: Dict[str, Any]
) -> bool:
    """
    Process Cashfree PG Webhook events (e.g. PAYMENT_SUCCESS_WEBHOOK or ORDER_PAID).
    """
    event_type = payload.get("type")
    data = payload.get("data", {})
    order_data = data.get("order", {})
    payment_data = data.get("payment", {})

    order_id = order_data.get("order_id")
    order_status = order_data.get("order_status")
    payment_status = payment_data.get("payment_status")
    payment_id = payment_data.get("cf_payment_id")

    if not order_id:
        return False

    if order_status == "PAID" or payment_status == "SUCCESS":
        stmt = select(Order).where(Order.order_id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        if order and order.status != "paid":
            order.status = "paid"
            order.gateway_payment_id = str(payment_id) if payment_id else "cf_webhook_paid"
            await record_fact_unlock(
                db=db,
                order_id=order.order_id,
                fact_id=order.fact_id,
                session_id=order.session_id
            )
            await db.commit()

    return True


async def process_razorpay_webhook(
    db: AsyncSession,
    payload: Dict[str, Any]
) -> bool:
    """Process asynchronous server-to-server webhook from Razorpay."""
    event = payload.get("event")
    if event not in ["payment.captured", "order.paid"]:
        return True

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_order_id = payment_entity.get("order_id")
    razorpay_payment_id = payment_entity.get("id")
    status_val = payment_entity.get("status")

    if not razorpay_order_id or status_val != "captured":
        return True

    stmt = select(Order).where(Order.gateway_order_id == razorpay_order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        return False

    if order.status != "paid":
        order.status = "paid"
        order.gateway_payment_id = razorpay_payment_id
        await record_fact_unlock(
            db=db,
            order_id=order.order_id,
            fact_id=order.fact_id,
            session_id=order.session_id
        )
        await db.commit()

    return True
