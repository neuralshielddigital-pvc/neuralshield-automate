"""Independent opt-in worker; never shares Automation workflow transactions."""
import logging
import threading
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.agency_delivery_service import AgencyDeliveryService

logger = logging.getLogger(__name__)
_stop = threading.Event()
_thread = None


def run_delivery_tick():
    if not settings.AGENCY_STARTER_DELIVERY_ENABLED:
        return
    db = SessionLocal()
    try:
        AgencyDeliveryService(db).run_batch()
    except Exception:
        db.rollback()
        # Provider exceptions could contain private content; log only a fixed code.
        logger.error('Agency delivery tick failed; inspect fulfilment status')
    finally:
        db.close()


def _loop():
    while not _stop.is_set():
        run_delivery_tick()
        _stop.wait(60)


def start_agency_delivery_worker():
    global _thread
    if not settings.AGENCY_STARTER_DELIVERY_ENABLED or (_thread and _thread.is_alive()):
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name='agency-starter-delivery', daemon=True)
    _thread.start()


def stop_agency_delivery_worker():
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=5)
