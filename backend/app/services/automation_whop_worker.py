"""Separate bounded reconciliation loop, so workflow execution is unaffected."""
from datetime import datetime, timedelta, timezone
import logging
import threading
import httpx
from sqlalchemy import select
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.automation_whop import AutomationWhopMembership
from app.services.automation_whop_service import AutomationWhopService, adapter

log = logging.getLogger(__name__)
_stop = threading.Event()
_thread = None


def tick():
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        ids = list(db.scalars(select(AutomationWhopMembership.membership_id)
            .where(AutomationWhopMembership.terminal.is_(False),
                   AutomationWhopMembership.checked_at < now - timedelta(minutes=4))
            .order_by(AutomationWhopMembership.checked_at).limit(100)))
    with httpx.Client(trust_env=False) as client:
        for membership_id in ids:
            if _stop.is_set():
                break
            with SessionLocal() as db:
                try:
                    AutomationWhopService(db, adapter(client)).refresh_membership(membership_id, now)
                    db.commit()
                except Exception:
                    db.rollback()
                    # Never log payloads, tokens, provider responses or personal IDs.
                    log.warning("Automation Whop reconciliation pending; paid snapshot will expire")


def loop():
    while not _stop.is_set():
        try:
            tick()
        except Exception:
            log.warning("Automation Whop reconciliation unavailable; paid snapshot will expire")
        _stop.wait(60)


def start():
    global _thread
    if not settings.AUTOMATION_WHOP_ENABLED or (_thread and _thread.is_alive()):
        return
    _stop.clear()
    _thread = threading.Thread(target=loop, name="automation-whop-reconciliation", daemon=True)
    _thread.start()


def stop():
    _stop.set()
    if _thread:
        _thread.join(timeout=10)
