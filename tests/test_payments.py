import pytest


@pytest.mark.asyncio
async def test_create_order_success(client):
    """Verify order creation sets correct ₹1 (100 paise) amount and returns order_id."""
    payload = {
        "fact_id": 1,
        "session_id": "test_user_session_abc123"
    }
    response = await client.post("/api/payments/create", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 100
    assert data["amount_inr"] == 1.0
    assert data["currency"] == "INR"
    assert "order_id" in data
    assert data["fact_id"] == 1


@pytest.mark.asyncio
async def test_verify_and_unlock_flow(client):
    """Test the complete flow: create order -> verify payment -> access unlocked fact."""
    session_id = "test_user_session_flow_99"
    
    # 1. Create order
    create_res = await client.post("/api/payments/create", json={
        "fact_id": 1,
        "session_id": session_id
    })
    assert create_res.status_code == 200
    order_data = create_res.json()
    order_id = order_data["order_id"]

    # 2. Before payment, fact is locked
    locked_check = await client.get(f"/api/facts/1?session_id={session_id}")
    assert locked_check.status_code == 402

    # 3. Verify payment (Simulator mode)
    verify_res = await client.post("/api/payments/verify", json={
        "order_id": order_id,
        "gateway_order_id": order_data.get("gateway_order_id"),
        "gateway_payment_id": "sim_pay_test_123",
        "gateway_signature": "sim_sig_ok",
        "session_id": session_id
    })
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["success"] is True
    assert verify_data["fact"] is not None
    assert "A day on Venus is longer" in verify_data["fact"]["fact_text"]

    # 4. Now the fact is unlocked for this session
    unlocked_res = await client.get(f"/api/facts/1?session_id={session_id}")
    assert unlocked_res.status_code == 200
    fact_data = unlocked_res.json()
    assert fact_data["is_unlocked"] is True
    assert fact_data["fact_text"] == "A day on Venus is longer than a year on Venus."
    assert "NASA" in fact_data["source_name"]


@pytest.mark.asyncio
async def test_duplicate_unlock_prevention(client):
    """Verify that creating an order for an already unlocked fact is prevented."""
    session_id = "test_user_session_dup_55"
    
    # Create & Pay
    create_res = await client.post("/api/payments/create", json={
        "fact_id": 2,
        "session_id": session_id
    })
    order_data = create_res.json()
    await client.post("/api/payments/verify", json={
        "order_id": order_data["order_id"],
        "gateway_payment_id": "sim_pay_55",
        "session_id": session_id
    })

    # Try creating another order for same fact on same session
    dup_res = await client.post("/api/payments/create", json={
        "fact_id": 2,
        "session_id": session_id
    })
    assert dup_res.status_code == 400
    assert "already unlocked" in dup_res.json()["detail"].lower()
