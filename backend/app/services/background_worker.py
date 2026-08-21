from __future__ import annotations

import logging
import os
import threading
import time

from app.core.database import SessionLocal
from app.services.gmail_poller import run_gmail_new_email_poll
from app.services.workflow_scheduler import run_due_scheduled_workflows
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

_stop_event = threading.Event()
_worker_thread: threading.Thread | None = None


def _worker_loop() -> None:
    interval_seconds = int(os.getenv("AUTOMATION_WORKER_INTERVAL_SECONDS", "60"))
    logger.info("Automation background worker started interval_seconds=%s", interval_seconds)

    while not _stop_event.is_set():
        db = SessionLocal()
        try:
            schedule_result = run_due_scheduled_workflows(db)
            retry_result = WorkflowService(db).run_due_retries()
            gmail_result = run_gmail_new_email_poll(db)

            logger.info(
                "Automation worker tick schedule=%s retries=%s gmail=%s",
                schedule_result,
                retry_result,
                gmail_result,
            )
        except Exception:
            logger.exception("Automation background worker tick failed")
        finally:
            db.close()

        _stop_event.wait(interval_seconds)

    logger.info("Automation background worker stopped")


def start_background_worker() -> None:
    global _worker_thread

    enabled = os.getenv("AUTOMATION_BACKGROUND_WORKER_ENABLED", "true").lower()
    if enabled not in {"1", "true", "yes", "on"}:
        logger.info("Automation background worker disabled")
        return

    if _worker_thread and _worker_thread.is_alive():
        return

    _stop_event.clear()
    _worker_thread = threading.Thread(target=_worker_loop, name="automation-background-worker", daemon=True)
    _worker_thread.start()


def stop_background_worker() -> None:
    _stop_event.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=10)
