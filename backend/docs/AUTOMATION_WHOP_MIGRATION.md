# Automation Whop migration — 24 November 2026

Scope: app.neuralshielddigital.com, monthly Starter USD19 / Pro USD59 /
Business USD149. Existing Agency one-time orders and Client Acquisition are
separate. Preserve historical subscriptions and payments; no automatic external
cancellations, customer conversions, manual grants, or duplicate payments.

This release is disabled by default. It is NOT a claim that billing is live.

## Ownership and access

An authenticated, email-verified application user creates an intent with the
user and tenant loaded from the database. The intent is committed before any
provider checkout. Its UUID is also the provider idempotency key. Advisory locks
serialize concurrent checkouts. Replays return the existing configuration;
pending plan changes and existing subscriptions require support.

Payment and membership must independently attest the exact server-owned intent
metadata, merchant, product, variant, USD settlement amount and current paid
period. This delegates an authorized checkout to its initiating application
account; it is not OAuth identity proof and cannot claim unrelated memberships.
Existing standalone OAuth/nonce claim guardrails are not relaxed or enabled.
Browser return, email equality and raw webhook payloads never grant access.

New paid entitlements expire at period end or after ten minutes without a
verified provider refresh. A separate worker checks stale records every minute
(after four minutes). A paid initial charge cannot prove an unpaid renewal.
Cancellation at period end retains the paid period. Verified refund evidence is
terminal; delayed positive events cannot restore it. Errors fail closed.

New Whop allowances match public pricing: Starter 10 workflows/500 runs,
Pro 50/20,000, Business unlimited/100,000; unlimited webhooks. Legacy allowances
and payment histories are unchanged. Local plan lookup includes name, price and
monthly interval so legacy Pro USD149 cannot be mistaken for Pro USD59.

## Production activation checklist

1. Require all backend, frontend and disposable PostgreSQL CI checks to pass.
2. Back up live backend/frontend code and PostgreSQL with restore verification.
   Compare live hotfixes before overlaying files; do not deploy stale main.
3. Apply additive migrations through 20261124_0003 with provider disabled.
   Install pinned httpx runtime dependency. Deploy immutable reviewed source.
4. Install a dedicated Automation credential privately; do not reuse the Agency
   or Client Acquisition key, expose secrets in chat, or put them in Git.
5. Configure a separate webhook at
   https://api.neuralshielddigital.com/api/webhooks/automation/whop,
   webhook API v1 date 2026-11-11. Authenticated resource reads remain pinned
   to 2026-11-07. Subscribe to payment.succeeded/payment.failed and
   membership.activated/membership.updated/membership.deactivated where supported.
   Install its signing secret privately. Verify the actual provider payload and
   retry contract. Unknown events/resources fail closed and are not acknowledged.
6. Configure the allowlisted live merchant and three verified product/plan pairs.
   Enable AUTOMATION_WHOP_ENABLED only after credentials, schema, worker and
   provider contract checks pass. This disables new Paddle checkout; historical
   Paddle webhooks remain for legacy lifecycle processing.
7. Verify live health, Agency regression, public pricing, logged-in billing,
   unauthenticated/foreign-tenant denial and actual Whop redirect.
8. User completes one reviewed real payment; verify webhook receipt, correct
   local account, paid period, limits, refresh and absence of duplicate charge.
   Never mark a checkout return or a test card as successful live payment.

## Rollback

Disable AUTOMATION_WHOP_ENABLED and restore reviewed application files and
process configuration. Preserve additive billing tables/history. Downgrade
refuses data loss if any new records exist. Never drop paid data or restore an
old database over new real payments. Reconcile any newly paid Whop customer
before resuming an older provider to avoid duplicate charges or lost access.
