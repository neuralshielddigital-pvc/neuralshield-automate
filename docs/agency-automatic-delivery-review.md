# Starter automatic delivery implementation

18 September 2026. Repository changes for review; no deployment, provider calls,
customer email, real payment or production migration performed.

## Implemented flow

The existing signature-verified Paddle webhook records a completed Starter order,
active entitlement and pending fulfilment in the database. A separate opt-in
worker polls that queue every 60 seconds, processing at most ten records per tick.

For each Starter fulfilment it:

1. Atomically claims the row with an incremented attempt number.
2. Fetches the transaction and customer from Paddle using the configured backend
   credentials, verifying their IDs, completed status and product price identity.
3. Uses the provider customer's validated email. Starter checkout `custom_data`
   cannot choose the delivery recipient or merge the buyer with another account.
   Legacy email mismatch or email uniqueness conflicts stop for review.
4. Checks SMTP configuration and rechecks the active entitlement.
5. Creates a hashed, expiring one-time access token, fences the send against the
   claimed attempt number and records `sending` before the external SMTP call.
6. Records `email_submitted` and `email_submitted_at` when SMTP returns success.
   This is not proof of inbox delivery; `delivered_at` remains unset.
7. Lets the buyer consume the link once and download purchased resources through
   the existing authenticated member routes.

The worker uses independent database sessions and does not reuse Automation's
workflow scheduler. It is disabled by default. Only Starter rows are selected;
other Agency products retain their existing manual delivery behavior. Their
content and trusted-identity automatic-delivery rollout are still separate work.

## Failure and duplicate behavior

| State | Meaning and next action |
| --- | --- |
| pending / pending_customer_enrichment | Eligible for first worker attempt. |
| processing | Claimed, before SMTP. |
| retry_wait | Provider/config/pre-send failure; retry after 60 then 300 seconds, maximum three attempts. |
| sending | SMTP boundary crossed. No second automatic send. |
| email_submitted | SMTP accepted the call; inbox receipt unverified. |
| failed | Attempts exhausted, mismatched identity or ineligible purchase; owner review. |
| delivery_unknown | SMTP raised, or worker disappeared during send. Inspect provider evidence; no automatic resend. |

Processing claims older than five minutes can be recovered with a new attempt
number. A stalled old worker cannot pass the new owner's send fence. Sending
claims older than five minutes become `delivery_unknown`, never automatic retries.
A process crash after SMTP acceptance but before committing the result may leave
an unknown outcome. Exactly-once inbox delivery is not claimed.

The admin fulfilments API exposes attempts, next-attempt time, claim time,
submission time and fixed error codes. Existing UI displays status and last error;
a richer operations UI is not part of this change. Raw provider exceptions,
message bodies and access tokens are not recorded as fulfilment errors.

Duplicate webhook notifications reuse the existing order. The worker's database
claim prevents competing workers from sending the same fulfilment twice. Link
consumption now uses an atomic database compare-and-set; expired, revoked, reused
links and inactive customers are rejected.

## Purchase validation

Base unit price and total paid are different when taxes apply. The commerce
handler validates the existing approved USD unit price, quantity one, one Agency
line item, non-recurring price and completed status, while storing the actual
positive transaction total. No prices are changed. Mixed carts, recurring prices,
unsupported currency and zero-total transactions remain rejected.

Provider contracts checked against Paddle's official documentation:
- https://developer.paddle.com/api-reference/customers/get-customer/
- https://developer.paddle.com/api-reference/transactions/get-transaction/
- https://developer.paddle.com/webhooks/transactions/transaction-completed/

## Verification

Initial automatic-delivery checkpoint: 81 focused local tests passed (22 dependency deprecation warnings). The follow-up [provider-validation readiness](agency-provider-validation-readiness.md) records 88 tests including real loopback SMTP, sandbox separation and the prepared PostgreSQL runner.

The focused local test command covers signed webhook receipt, duplicate event and
transaction IDs, trusted email lookup, link consumption, ZIP download, invalid
signatures, identity mismatches, revoked purchases, retry limits, stale claims,
SMTP uncertainty, disabled worker behavior, tax-inclusive totals, price guards,
SQLite migration round-trip, competing worker sessions and existing billing tests.

Provider calls remain fakes. Initial delivery tests use fake SMTP; the follow-up also tests real SMTP against a loopback receiver only. Tests use synthetic
identities and temporary SQLite only. PostgreSQL migration SQL was generated
without a database connection. These checks are not hosted PostgreSQL or real
Paddle/SMTP acceptance evidence. Existing FastAPI/python-jose deprecation warnings
remain.

## Concrete deployment requirements

Do not deploy until the owner authorizes an exact target and release after test
validation. This backend also serves Automation, so reconcile its current release
before merging or promoting any branch.

- Additive migration: `20260831_0003` to `20260918_0004`, adding four fulfilment
  tracking columns. Stage and verify on isolated PostgreSQL before production.
- Feature flag: `AGENCY_STARTER_DELIVERY_ENABLED=false` by default. Keep false
  through migration and initial deployment. Enabling it also processes existing
  pending Starter fulfilments; inspect that backlog before activation.
- Existing Paddle configuration must target the intended environment and have
  `customer.read` and transaction-read permissions. Never place credentials in
  the repo or chat. Production price IDs remain fixed. A real sandbox test uses the separately configured `AGENCY_STARTER_SANDBOX_PRICE_ID`, plus an approved test recipient and member URL; see the follow-up readiness document.
- Existing SMTP configuration and sender must be verified. A bounded test needs
  an approved owner-controlled recipient. No marketing emails are introduced.
- Run a controlled provider payment/access/download test, including failure and
  replay cases. Verify provider tax/currency behavior and refund/chargeback access
  revocation before claiming complete sales readiness. This change checks local
  entitlement revocation but does not implement Paddle refund reconciliation.
- For rollback, disable the worker and restore the prior application release.
  Retain the additive columns and attempt history. Do not clear `sending` or
  `delivery_unknown` rows to force a resend without investigating the outcome.

A successful local test does not authorize deployment or sending a real email.
