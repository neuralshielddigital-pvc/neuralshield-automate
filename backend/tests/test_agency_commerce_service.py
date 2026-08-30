from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services.agency_commerce_service import (
    AGENCY_PRICE_CATALOG,
    AgencyCommerceService,
)


def payload(
    price_id: str,
    amount_cents: str,
) -> dict:
    return {
        "id": "txn_test_agency_001",
        "customer_id": "ctm_test_001",
        "currency_code": "USD",
        "items": [
            {
                "price": {
                    "id": price_id,
                }
            }
        ],
        "details": {
            "totals": {
                "total": amount_cents,
            }
        },
    }


@pytest.mark.parametrize(
    ("price_id", "product_key", "amount"),
    [
        (
            "pri_01kzx9mrs5g2bxgjgqwfcb4med",
            "starter-toolkit",
            Decimal("27.00"),
        ),
        (
            "pri_01m1a363nz4srjzs7qh7jk7zhw",
            "pro-communications",
            Decimal("67.00"),
        ),
        (
            "pri_01m1a37y66za25g2ahv2vqf0qy",
            "advanced-operations",
            Decimal("97.00"),
        ),
        (
            "pri_01m1a3a4j9d19nmcy54bfd8wgw",
            "agency-commercial-license",
            Decimal("197.00"),
        ),
    ],
)
def test_exact_agency_catalog(
    price_id: str,
    product_key: str,
    amount: Decimal,
) -> None:
    assert AGENCY_PRICE_CATALOG[price_id] == {
        "product_key": product_key,
        "amount": amount,
    }


def test_non_agency_price_not_routed() -> None:
    service = AgencyCommerceService(db=None)  # type: ignore[arg-type]

    assert (
        service.is_agency_transaction(
            payload("pri_not_agency", "1900")
        )
        is False
    )


def test_agency_price_detected_without_customer_email() -> None:
    service = AgencyCommerceService(db=None)  # type: ignore[arg-type]

    assert (
        service.is_agency_transaction(
            payload(
                "pri_01kzx9mrs5g2bxgjgqwfcb4med",
                "2700",
            )
        )
        is True
    )


def test_multiple_agency_products_rejected() -> None:
    service = AgencyCommerceService(db=None)  # type: ignore[arg-type]

    data = payload(
        "pri_01kzx9mrs5g2bxgjgqwfcb4med",
        "2700",
    )

    data["items"].append(
        {
            "price": {
                "id": "pri_01m1a363nz4srjzs7qh7jk7zhw"
            }
        }
    )

    with pytest.raises(HTTPException) as exc:
        service.is_agency_transaction(data)

    assert exc.value.status_code == 400


def test_amount_parser() -> None:
    service = AgencyCommerceService(db=None)  # type: ignore[arg-type]

    assert service._extract_total_usd(
        payload(
            "pri_01m1a37y66za25g2ahv2vqf0qy",
            "9700",
        )
    ) == Decimal("97.00")
