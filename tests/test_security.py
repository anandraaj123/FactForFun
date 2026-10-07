import pytest


@pytest.mark.asyncio
async def test_admin_auth_required(client):
    """Verify admin endpoints reject requests without valid X-Admin-Key header."""
    # No header
    res_no_auth = await client.get("/api/admin/stats")
    assert res_no_auth.status_code == 401

    # Wrong header
    res_wrong_auth = await client.get("/api/admin/stats", headers={"X-Admin-Key": "wrong_key"})
    assert res_wrong_auth.status_code == 401

    # Valid header
    res_valid_auth = await client.get("/api/admin/stats", headers={"X-Admin-Key": "test_admin_secret_key"})
    assert res_valid_auth.status_code == 200
    stats = res_valid_auth.json()
    assert "total_facts" in stats


@pytest.mark.asyncio
async def test_session_mismatch_protection(client):
    """Verify that User B cannot verify or steal User A's order."""
    session_a = "user_session_alice_111"
    session_b = "user_session_bob_222"

    # Alice creates order
    res = await client.post("/api/payments/create", json={
        "fact_id": 1,
        "session_id": session_a
    })
    assert res.status_code == 200
    order_id = res.json()["order_id"]

    # Bob attempts to verify Alice's order with Bob's session
    steal_attempt = await client.post("/api/payments/verify", json={
        "order_id": order_id,
        "gateway_payment_id": "sim_pay_attacker",
        "session_id": session_b
    })
    assert steal_attempt.status_code == 403
    assert "session mismatch" in steal_attempt.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sql_injection_resilience(client):
    """Verify that SQL injection strings in category or search are handled safely."""
    malicious_query = "' OR 1=1 --"
    res = await client.get(f"/api/facts/teaser?category={malicious_query}")
    # Should safely return 404 or a legitimate filtered result, not execute arbitrary SQL
    assert res.status_code in [200, 404]
