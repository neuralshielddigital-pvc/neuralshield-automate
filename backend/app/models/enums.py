from enum import Enum


class UserRole(Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class PlanInterval(Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatus(str, Enum):
    INCOMPLETE = "INCOMPLETE"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"


class CommissionStatus(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"


class CampaignStatus(Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class CampaignType(Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


class CampaignExecutionStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class LeadStage(Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    WON = "WON"
    LOST = "LOST"


class WorkflowRunStatus(Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowTriggerType(Enum):
    WEBHOOK_RECEIVED = "WEBHOOK_RECEIVED"
    SCHEDULED = "SCHEDULED"
    NEW_LEAD = "NEW_LEAD"
    CAMPAIGN_ACTIVATED = "CAMPAIGN_ACTIVATED"
    GMAIL_NEW_EMAIL = "GMAIL_NEW_EMAIL"
    SLACK_NEW_MESSAGE = "SLACK_NEW_MESSAGE"


class WorkflowActionType(Enum):
    SEND_WEBHOOK = "SEND_WEBHOOK"
    SEND_EMAIL = "SEND_EMAIL"
    CREATE_LEAD = "CREATE_LEAD"
    ADD_AUDIT_LOG = "ADD_AUDIT_LOG"
    WAIT = "WAIT"
    CONDITION = "CONDITION"
    HTTP_REQUEST = "HTTP_REQUEST"
    UPDATE_LEAD = "UPDATE_LEAD"
    TAG_LEAD = "TAG_LEAD"
    GOOGLE_SHEETS_APPEND = "GOOGLE_SHEETS_APPEND"
    SLACK_SEND_MESSAGE = "SLACK_SEND_MESSAGE"
    OPENAI_TEXT_GENERATE = "OPENAI_TEXT_GENERATE"
