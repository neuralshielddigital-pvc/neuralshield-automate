from fastapi import HTTPException

from app.api.routes.agency_admin import require_super_admin
from app.models.enums import UserRole


class DummyUser:
    def __init__(self, role):
        self.role = role


def test_super_admin_allowed() -> None:
    user = DummyUser(UserRole.SUPER_ADMIN)
    assert require_super_admin(user) is user


def test_non_super_admin_forbidden() -> None:
    user = DummyUser(UserRole.ADMIN)

    try:
        require_super_admin(user)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Expected HTTP 403")


def test_agency_admin_route_prefix_registered() -> None:
    from app.api.router import api_router

    paths = {
        route.path
        for route in api_router.routes
    }

    expected = {
        "/agency-admin/overview",
        "/agency-admin/leads",
        "/agency-admin/customers",
        "/agency-admin/orders",
        "/agency-admin/entitlements",
        "/agency-admin/fulfilments",
    }

    assert expected.issubset(paths)
