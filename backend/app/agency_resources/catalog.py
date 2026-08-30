from __future__ import annotations

from pathlib import Path
from typing import Any


RESOURCE_ROOT = Path(__file__).resolve().parent / "content"


RESOURCE_CATALOG: dict[str, dict[str, Any]] = {
    "starter-client-intake": {
        "product_key": "starter-toolkit",
        "title": "Client Intake Checklist",
        "description": "A practical intake checklist for new agency prospects.",
        "filename": "starter-client-intake.md",
        "media_type": "text/markdown",
    },
    "starter-discovery": {
        "product_key": "starter-toolkit",
        "title": "Discovery Questionnaire",
        "description": "Structured discovery questions for first client calls.",
        "filename": "starter-discovery-questionnaire.md",
        "media_type": "text/markdown",
    },
    "starter-pipeline": {
        "product_key": "starter-toolkit",
        "title": "Pipeline Tracker",
        "description": "CSV template for prospect and opportunity tracking.",
        "filename": "starter-pipeline-tracker.csv",
        "media_type": "text/csv",
    },
    "pro-outreach": {
        "product_key": "pro-communications",
        "title": "Agency Outreach Sequence",
        "description": "Multi-touch outreach framework for qualified prospects.",
        "filename": "pro-outreach-sequence.md",
        "media_type": "text/markdown",
    },
    "pro-follow-up": {
        "product_key": "pro-communications",
        "title": "Follow-up Message Library",
        "description": "Short follow-up patterns for common prospect states.",
        "filename": "pro-follow-up-library.md",
        "media_type": "text/markdown",
    },
    "pro-proposal": {
        "product_key": "pro-communications",
        "title": "Proposal Outline",
        "description": "Reusable proposal structure for agency engagements.",
        "filename": "pro-proposal-outline.md",
        "media_type": "text/markdown",
    },
    "advanced-delivery": {
        "product_key": "advanced-operations",
        "title": "Client Delivery SOP",
        "description": "Operational SOP for onboarding and client delivery.",
        "filename": "advanced-delivery-sop.md",
        "media_type": "text/markdown",
    },
    "advanced-scorecard": {
        "product_key": "advanced-operations",
        "title": "Weekly Operations Scorecard",
        "description": "CSV scorecard for delivery, pipeline and retention signals.",
        "filename": "advanced-weekly-scorecard.csv",
        "media_type": "text/csv",
    },
    "advanced-health": {
        "product_key": "advanced-operations",
        "title": "Client Health Review",
        "description": "Monthly client health and renewal review framework.",
        "filename": "advanced-client-health-review.md",
        "media_type": "text/markdown",
    },
    "commercial-guide": {
        "product_key": "agency-commercial-license",
        "title": "Commercial-Use Operations Guide",
        "description": (
            "Operational guidance for using eligible purchased assets "
            "in client-service delivery, subject to published licence terms."
        ),
        "filename": "commercial-use-guide.md",
        "media_type": "text/markdown",
    },
}


def resources_for_products(
    product_keys: set[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for resource_id, item in RESOURCE_CATALOG.items():
        if item["product_key"] not in product_keys:
            continue

        result.append(
            {
                "id": resource_id,
                "product_key": item["product_key"],
                "title": item["title"],
                "description": item["description"],
                "media_type": item["media_type"],
            }
        )

    return result
