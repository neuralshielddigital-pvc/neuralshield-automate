"""Agency Whop feature configuration; fail closed until fully provisioned."""
from app.core.config import settings


def configured_agency_whop_products() -> dict[str, str]:
    if not settings.AGENCY_WHOP_ENABLED:
        return {}
    values = {
        settings.AGENCY_WHOP_PRODUCT_STARTER_ID: "starter-toolkit",
        settings.AGENCY_WHOP_PRODUCT_PRO_ID: "pro-communications",
        settings.AGENCY_WHOP_PRODUCT_ADVANCED_ID: "advanced-operations",
        settings.AGENCY_WHOP_PRODUCT_LICENSE_ID: "agency-commercial-license",
    }
    ids = list(values)
    if (
        len(ids) != 4
        or any(not item or not item.strip() for item in ids)
        or len(set(ids)) != 4
        or not settings.AGENCY_WHOP_API_KEY.strip()
        or not settings.AGENCY_WHOP_WEBHOOK_SECRET.strip()
    ):
        raise ValueError("Whop enabled but product mapping or credentials are incomplete")
    return values
