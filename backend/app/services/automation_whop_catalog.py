"""Approved monthly Automation prices and the public plan allowances."""
from app.services.automation_whop_contract import Plan
from app.services.automation_whop_transport import WhopBinding, WhopError

VERSION = "automation-whop-20261124-v1"
PRICES = {"starter": 1900, "pro": 5900, "business": 14900}
LIMITS = {
    "starter": {"workflows": 10, "monthly_runs": 500, "webhooks": -1},
    "pro": {"workflows": 50, "monthly_runs": 20000, "webhooks": -1},
    "business": {"workflows": -1, "monthly_runs": 100000, "webhooks": -1},
}
LOCAL_NAMES = {"starter": "Starter", "pro": "Pro", "business": "Enterprise"}


def plan_for(code: str) -> Plan:
    if code == "enterprise":
        code = "business"
    if code not in PRICES:
        raise WhopError("unknown_automation_plan")
    return Plan(VERSION, code, "USD", "month", PRICES[code], code + "-v1")


def binding_for(code: str, settings) -> WhopBinding:
    plan = plan_for(code)
    prefix = "AUTOMATION_WHOP_" + plan.code.upper()
    return WhopBinding(VERSION, plan.code, getattr(settings, prefix + "_PRODUCT_ID"), getattr(settings, prefix + "_PLAN_ID"), plan.amount_minor, "month")
