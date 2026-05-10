from enum import StrEnum


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class PlanInterval(StrEnum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    PAST_DUE = "PAST_DUE"
    INCOMPLETE = "INCOMPLETE"


class CommissionStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"


class CampaignStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class CampaignType(StrEnum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


class CampaignExecutionStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class LeadStage(StrEnum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    WON = "WON"
    LOST = "LOST"


class WorkflowRunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowTriggerType(StrEnum):
    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"
    NEW_LEAD = "NEW_LEAD"
    CAMPAIGN_ACTIVATED = "CAMPAIGN_ACTIVATED"


class WorkflowActionType(StrEnum):
    SEND_WEBHOOK = "SEND_WEBHOOK"
    SEND_EMAIL = "SEND_EMAIL"
    CREATE_LEAD = "CREATE_LEAD"
    ADD_AUDIT_LOG = "ADD_AUDIT_LOG"
