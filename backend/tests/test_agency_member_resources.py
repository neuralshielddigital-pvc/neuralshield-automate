from app.agency_resources import (
    RESOURCE_CATALOG,
    resources_for_products,
)
from app.agency_resources.catalog import RESOURCE_ROOT


def test_all_catalog_files_exist() -> None:
    for item in RESOURCE_CATALOG.values():
        assert (RESOURCE_ROOT / item["filename"]).is_file()


def test_starter_does_not_receive_pro_resources() -> None:
    items = resources_for_products(
        {"starter-toolkit"}
    )

    assert items
    assert all(
        item["product_key"] == "starter-toolkit"
        for item in items
    )


def test_multi_entitlement_returns_union_only() -> None:
    products = {
        "starter-toolkit",
        "pro-communications",
    }

    items = resources_for_products(products)

    assert {
        item["product_key"]
        for item in items
    } == products


def test_member_resource_routes_registered() -> None:
    from app.api.router import api_router

    paths = {
        route.path
        for route in api_router.routes
    }

    assert "/agency-member/resources" in paths
    assert (
        "/agency-member/resources/{resource_id}"
        in paths
    )
