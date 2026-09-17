"""Durable Starter fulfilment. No SMTP retries after an uncertain send outcome."""
from datetime import datetime, timedelta, timezone
import re
from functools import partial
from urllib.parse import urlsplit

from email_validator import validate_email, EmailNotValidError
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.models.agency_commerce import AgencyCustomer, AgencyOrder, AgencyEntitlement, AgencyFulfilment
from app.services.agency_commerce_service import AgencyCommerceService
from app.services.agency_member_service import AgencyMemberService
from app.services.email_service import EmailService
from app.services.paddle_service import PaddleService


class DeliveryIssue(Exception):
    def __init__(self, code, retryable=False):
        self.code = code
        self.retryable = retryable


class AgencyDeliveryService:
    MAX_ATTEMPTS = 3
    RETRY_SECONDS = (60, 300)
    READY = ('pending', 'pending_customer_enrichment', 'retry_wait')

    def __init__(self, db, provider=None, emailer=None):
        self.db = db
        self.provider = provider or PaddleService(db)
        self.emailer = emailer or EmailService()

    def run_batch(self, limit=10):
        if not settings.AGENCY_STARTER_DELIVERY_ENABLED:
            return {'enabled': False, 'processed': 0}
        now = datetime.now(timezone.utc)
        # A crash before SMTP is retryable. A crash during SMTP is never retried.
        self.db.execute(update(AgencyFulfilment).where(
            AgencyFulfilment.status == 'processing',
            AgencyFulfilment.claimed_at < now - timedelta(minutes=5),
        ).values(status='retry_wait', next_attempt_at=now, last_error='pre_send_worker_interrupted'))
        self.db.execute(update(AgencyFulfilment).where(
            AgencyFulfilment.status == 'sending',
            AgencyFulfilment.claimed_at < now - timedelta(minutes=5),
        ).values(status='delivery_unknown', last_error='smtp_outcome_unknown'))
        self.db.execute(update(AgencyFulfilment).where(
            AgencyFulfilment.status.in_(self.READY),
            AgencyFulfilment.attempt_count >= self.MAX_ATTEMPTS,
        ).values(status='failed', last_error='attempt_limit_reached'))
        self.db.commit()
        ids = self.db.scalars(select(AgencyFulfilment.id).join(
            AgencyEntitlement, AgencyFulfilment.entitlement_id == AgencyEntitlement.id,
        ).where(
            AgencyEntitlement.product_key == 'starter-toolkit',
            AgencyFulfilment.status.in_(self.READY),
            AgencyFulfilment.attempt_count < self.MAX_ATTEMPTS,
            or_(AgencyFulfilment.next_attempt_at.is_(None), AgencyFulfilment.next_attempt_at <= now),
        ).order_by(AgencyFulfilment.created_at).limit(min(max(limit, 1), 10))).all()
        processed = sum(self.process_one(identifier) for identifier in ids)
        return {'enabled': True, 'processed': processed}

    def process_one(self, identifier):
        if not settings.AGENCY_STARTER_DELIVERY_ENABLED:
            return False
        now = datetime.now(timezone.utc)
        eligible = select(AgencyEntitlement.id).where(AgencyEntitlement.product_key == 'starter-toolkit')
        claimed = self.db.execute(update(AgencyFulfilment).where(
            AgencyFulfilment.id == identifier,
            AgencyFulfilment.entitlement_id.in_(eligible),
            AgencyFulfilment.status.in_(self.READY),
            AgencyFulfilment.attempt_count < self.MAX_ATTEMPTS,
            or_(AgencyFulfilment.next_attempt_at.is_(None), AgencyFulfilment.next_attempt_at <= now),
        ).values(status='processing', claimed_at=now,
                 attempt_count=AgencyFulfilment.attempt_count + 1, next_attempt_at=None)
            .returning(AgencyFulfilment.attempt_count))
        attempt = claimed.scalar_one_or_none()
        self.db.commit()
        if attempt is None:
            return False
        row = self.db.get(AgencyFulfilment, identifier)
        fail = partial(self._failure, identifier, expected_attempt=attempt)
        try:
            entitlement, order, customer = self._eligible(row)
            email = self._verified_email(order, customer)
            customer.email = email
            row.destination = email
            self.db.commit()
            # Validate SMTP configuration BEFORE creating a token or attempting send.
            self.emailer._validate_config()
        except DeliveryIssue as exc:
            fail(exc.code, exc.retryable)
            return True
        except IntegrityError:
            fail('customer_email_conflict', False)
            return True
        except ValueError:
            fail('smtp_configuration_missing', True)
            return True
        except Exception:
            fail('pre_send_failure', True)
            return True

        # Recheck entitlement immediately before preparing the send.
        self.db.expire_all()
        row = self.db.get(AgencyFulfilment, identifier)
        try:
            _, _, customer = self._eligible(row)
            token = AgencyMemberService(self.db)._create_access_token(customer.id)
            body = AgencyMemberService.access_email_body(token)
        except DeliveryIssue as exc:
            fail(exc.code, False)
            return True
        except Exception:
            fail('access_link_creation_failed', True)
            return True
        # Persist the at-most-one automatic SMTP attempt before crossing its boundary.
        sending = self.db.execute(update(AgencyFulfilment).where(
            AgencyFulfilment.id == identifier,
            AgencyFulfilment.status == 'processing',
            AgencyFulfilment.attempt_count == attempt,
        ).values(status='sending', claimed_at=datetime.now(timezone.utc)))
        self.db.commit()
        if sending.rowcount != 1:
            return True
        try:
            self.emailer.send_email(
                to_email=customer.email,
                subject='Your NeuralShield Agency Starter Toolkit access',
                body=body,
            )
        except Exception:
            fail('smtp_outcome_unknown', False, 'delivery_unknown')
            return True
        row.status = 'email_submitted'
        row.email_submitted_at = datetime.now(timezone.utc)
        row.last_error = None
        # delivered_at is intentionally unset: SMTP submission is not inbox delivery.
        self.db.commit()
        return True

    def _eligible(self, row):
        entitlement = self.db.get(AgencyEntitlement, row.entitlement_id)
        if entitlement is None or entitlement.status != 'active':
            raise DeliveryIssue('entitlement_inactive')
        order = self.db.get(AgencyOrder, entitlement.order_id)
        customer = self.db.get(AgencyCustomer, entitlement.customer_id)
        if (order is None or customer is None or order.status != 'completed'
                or customer.status != 'active' or order.customer_id != customer.id
                or order.product_key != entitlement.product_key):
            raise DeliveryIssue('purchase_not_eligible')
        return entitlement, order, customer

    def _verified_email(self, order, customer):
        environment = settings.PADDLE_ENVIRONMENT.strip().lower()
        expected_base = {'production': 'https://api.paddle.com', 'sandbox': 'https://sandbox-api.paddle.com'}.get(environment)
        if environment == 'sandbox':
            member_host = urlsplit(settings.AGENCY_MEMBER_BASE_URL).hostname
            if member_host in ('agency.neuralshielddigital.com', 'app.neuralshielddigital.com'):
                raise DeliveryIssue('sandbox_member_url_unsafe')
        if (not settings.PADDLE_API_KEY or not expected_base
                or settings.PADDLE_API_BASE_URL.rstrip('/') != expected_base):
            raise DeliveryIssue('paddle_configuration_missing', True)
        if (not re.fullmatch(r'txn_[a-z0-9]{26}', order.paddle_transaction_id or '')
                or not re.fullmatch(r'ctm_[a-z0-9]{26}', customer.paddle_customer_id or '')):
            raise DeliveryIssue('provider_identifier_invalid')
        try:
            transaction = self.provider._api_request('GET', '/transactions/' + order.paddle_transaction_id).get('data')
            remote = self.provider._api_request('GET', '/customers/' + customer.paddle_customer_id).get('data')
        except Exception:
            raise DeliveryIssue('paddle_lookup_failed', True) from None
        if (not isinstance(transaction, dict) or transaction.get('id') != order.paddle_transaction_id
                or transaction.get('status') != 'completed'
                or transaction.get('customer_id') != customer.paddle_customer_id):
            raise DeliveryIssue('provider_transaction_mismatch')
        match = AgencyCommerceService(self.db)._extract_agency_price(transaction)
        if match is None or match[0] != order.paddle_price_id:
            raise DeliveryIssue('provider_price_mismatch')
        if (not isinstance(remote, dict) or remote.get('id') != customer.paddle_customer_id
                or remote.get('status') != 'active'):
            raise DeliveryIssue('provider_customer_mismatch')
        try:
            email = validate_email(remote.get('email', ''), check_deliverability=False).normalized.lower()
        except (EmailNotValidError, TypeError):
            raise DeliveryIssue('provider_email_invalid') from None
        if environment == 'sandbox' and email != settings.AGENCY_DELIVERY_TEST_RECIPIENT.strip().lower():
            raise DeliveryIssue('sandbox_recipient_not_allowed')
        # Legacy checkout-provided identities are not silently reassigned.
        if customer.email and customer.email.lower() != email:
            raise DeliveryIssue('customer_email_mismatch')
        return email

    def _failure(self, identifier, code, retryable, terminal='failed', *, expected_attempt):
        self.db.rollback()
        values = {"last_error": code, "next_attempt_at": None, "status": terminal}
        if retryable and expected_attempt < self.MAX_ATTEMPTS:
            values.update(status="retry_wait", next_attempt_at=(
                datetime.now(timezone.utc)
                + timedelta(seconds=self.RETRY_SECONDS[expected_attempt - 1])
            ))
        self.db.execute(update(AgencyFulfilment).where(
            AgencyFulfilment.id == identifier,
            AgencyFulfilment.attempt_count == expected_attempt,
            AgencyFulfilment.status.in_(("processing", "sending")),
        ).values(**values))
        self.db.commit()
