"""SQLAlchemy table mapping for persistent, single-use Whop SaaS authorization.

The authorization service must generate cryptographically random nonces and
persist them before redirecting to a trusted provider authorization flow.
This table alone does not authenticate provider ownership or grant access.
"""
from sqlalchemy import Column, DateTime, MetaData, String, Table

whop_saas_ownership_nonces = Table(
    "whop_saas_ownership_nonces",
    MetaData(),
    Column("nonce", String(256), primary_key=True, nullable=False),
    Column("session_id", String(256), nullable=False),
    Column("user_id", String(256), nullable=False),
    Column("tenant_id", String(256), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("consumed_at", DateTime(timezone=True), nullable=True),
)
