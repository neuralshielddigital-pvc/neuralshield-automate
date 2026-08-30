from app.services.agency_member_service import (
    AgencyMemberService,
)


def test_member_token_hash_is_deterministic() -> None:
    raw = "example-secure-member-token"

    assert (
        AgencyMemberService._hash_token(raw)
        == AgencyMemberService._hash_token(raw)
    )


def test_member_token_hash_does_not_store_raw_token() -> None:
    raw = "example-secure-member-token"
    hashed = AgencyMemberService._hash_token(raw)

    assert hashed != raw
    assert len(hashed) == 64


def test_member_routes_registered() -> None:
    from app.api.router import api_router

    paths = {route.path for route in api_router.routes}

    assert "/agency-member/request-access" in paths
    assert "/agency-member/consume" in paths
