from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.services.affiliate_service import AffiliateService


def test_affiliate_register_referrals_and_commissions(client, monkeypatch):
    now = datetime.now(UTC).isoformat()
    affiliate_id = str(uuid4())
    referral_id = str(uuid4())

    monkeypatch.setattr(
        AffiliateService,
        "register_affiliate",
        lambda self, user: {
            "is_registered": True,
            "affiliate": {
                "id": affiliate_id,
                "user_id": str(user.id),
                "referral_code": "NSD123",
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            "referral_link": "http://localhost:3000/signup?ref=NSD123",
        },
    )
    monkeypatch.setattr(
        AffiliateService,
        "get_referrals",
        lambda self, user: [
            {
                "id": referral_id,
                "affiliate_id": affiliate_id,
                "referred_user_id": str(uuid4()),
                "referred_user_email": "lead@example.com",
                "created_at": now,
            }
        ],
    )
    monkeypatch.setattr(
        AffiliateService,
        "get_commissions",
        lambda self, user: [
            {
                "id": str(uuid4()),
                "affiliate_id": affiliate_id,
                "referral_id": referral_id,
                "amount": "25.00",
                "status": "PENDING",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    assert client.post("/api/affiliate/register").status_code == 201
    assert client.get("/api/affiliate/referrals").json()[0]["referred_user_email"] == "lead@example.com"
    assert client.get("/api/affiliate/commissions").json()[0]["status"] == "PENDING"
