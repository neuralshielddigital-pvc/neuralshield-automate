"""SQLAlchemy atomic nonce redemption for authenticated Whop ownership claims.

The caller must provision a table with nonce (unique), session_id, user_id,
tenant_id, expires_at (timezone-aware), and consumed_at (nullable). This adapter
does not mint tokens, infer provider ownership, or grant paid access.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Table, and_, update
from sqlalchemy.orm import Session


class SQLAlchemyAtomicAuthorizationStore:
    """Single-statement compare-and-consume, safe across concurrent workers.

    The caller owns transaction boundaries. Commit immediately after a successful
    redemption and binding creation in the same transaction; rollback on failure.
    """

    def __init__(self, db: Session, table: Table) -> None:
        required = {"nonce", "session_id", "user_id", "tenant_id", "expires_at", "consumed_at"}
        if not required.issubset(set(table.c.keys())):
            raise ValueError("Authorization nonce table is missing required columns")
        if not any(
            constraint.unique and {"nonce"} == set(constraint.columns.keys())
            for constraint in table.constraints
            if hasattr(constraint, "unique") and hasattr(constraint, "columns")
        ) and not any(
            index.unique and {"nonce"} == set(index.columns.keys())
            for index in table.indexes
        ) and not table.c.nonce.primary_key:
            raise ValueError("Nonce must be uniquely constrained")
        self.db = db
        self.table = table

    def consume_if_matches(
        self, *, nonce: str, session_id: str, user_id: str,
        tenant_id: str, now: datetime,
    ) -> bool:
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("An aware redemption timestamp is required")
        statement = (
            update(self.table)
            .where(and_(
                self.table.c.nonce == nonce,
                self.table.c.session_id == session_id,
                self.table.c.user_id == user_id,
                self.table.c.tenant_id == tenant_id,
                self.table.c.expires_at > now,
                self.table.c.consumed_at.is_(None),
            ))
            .values(consumed_at=now)
        )
        result = self.db.execute(statement)
        if result.rowcount not in (0, 1):
            raise RuntimeError("Nonce uniqueness invariant violated")
        return result.rowcount == 1
