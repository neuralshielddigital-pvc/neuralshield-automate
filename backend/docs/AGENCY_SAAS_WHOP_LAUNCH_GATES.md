# Whop recurring Workflow Automation SaaS — production release gates

**Date:** 2026-11-16. **Status: NOT LIVE / NOT ACCEPTED. Webhook event selection verified.**
This document covers the **monthly Workflow Automation SaaS** only.
It is NOT the one-time Agency Client Engine Whop product flow (which has
separate product IDs, order fulfilment and historical deployment).

## Checked against the signed-in Whop merchant dashboard

Whop business: `biz_v89TqnjOiedw0Z`.

| Tier | Product | Checkout plan | USD recurring price | Checkout-link visibility |
|---|---|---|---|---|
| Starter | `prod_i6Ll01S4m3jmI` | `plan_Ne9TiMmqGDAIC` | $19 every 1 month | Visible |
| Pro | `prod_09hIJdUshmzoA` | `plan_xZZtWwn50xkOE` | $59 every 1 month | Visible |
| Business | `prod_DFLx2nCufCLZa` | `plan_PLomodl9gQOJC` | $149 every 1 month | Hidden |

Prices, product-to-plan mappings, and monthly recurrence were inspected
read-only in Whop on 2026-11-16. No unintended zero-dollar plan was seen.
**A visible checkout link is not evidence that subscription fulfilment works.**
Product store visibility and link visibility are separate settings. Do not
enable Business or advertise any paid plan until all gates below pass.

Another Starter plan `plan_quU5KSASPY0bU` existed previously; never remove
or redirect it without verifying existing dependencies.

## Release must pass all these gates — currently blocked

1. **Provider contract:** independently confirm the real Whop authenticated
   membership/subscription REST resource, response fields, statuses, customer
   identity, plan/price/interval semantics and webhook event payloads against
   official versioned contract. The existing one-time `WhopProvider.purchase`
   explicitly rejects recurring purchases; never repurpose it as a SaaS grant.
   A synthetic provider implementation does not establish this contract.
2. **Whop event delivery: event selection DONE; signed SaaS delivery pending.**
   Existing active webhook `https://api.neuralshielddigital.com/api/webhooks/agency/whop`
   remains unchanged. On 2026-11-16 the signed-in Whop dashboard was edited,
   saved (success confirmation) and reopened: all **10** events persisted,
   including the required `membership.activated`, `membership.deactivated`,
   `membership.cancel_at_period_end_changed`, `membership.updated`,
   `payment.succeeded`, `payment.failed`, `refund.created`, `refund.updated`
   plus preexisting unrelated `ad.created`, `card_application.denied`.
   No webhook secret, endpoint URL or preexisting events were changed.
   Operator evidence: https://agent.tinyfish.ai/runs/5bd4f18e-7c79-4f06-ae25-b845a8c96c0b .
   **Still blocked:** real signed membership/payment delivery into an authenticated
   provider-backed **SaaS** handler and verified tenant entitlements. The present
   production handler is a one-time Agency handler; event subscriptions alone
   cannot grant paid SaaS access. A synthetic `product.updated` returned HTTP 200
   and `{"handled":false}`; that proves transport only.
3. **Authenticated buyer binding:** implement and validate an actual
   provider-authorized account-ownership flow tied to the logged-in SaaS
   principal and tenant. A checkout email, subscription ID, unverified
   redirect or signed webhook does **not** establish account ownership.
   The current `agency_saas_whop_claim.py` has a trusted-proof protocol,
   but no production proof issuance/callback yet.
4. **Fulfilment:** connect the independently verified provider adapter to
   the signed HTTP webhook handler and transactional Whop SaaS repository;
   verify first paid activation, idempotent retry, renewal, past-due and
   payment-failed changes, cancel/refund revocation and business-tier
   entitlement. One-time Agency purchases and Paddle subscriptions must
   continue to work unchanged.
5. **Reconciliation:** install and monitor a real scheduled provider lookup
   with due-item alerting, bounded batches, retry and outage policy.
   The existing pure reconciliation library is **not a live scheduled job**.
   Whop paid limits intentionally reject provider snapshots older than 24 h;
   do not enable those limits until a working refresh job prevents legitimate
   paying customer access from expiring.
6. **Deployment:** identify Sydney backend runtime and establish an approved
   authenticated deployment channel, snapshot/backup/rollback and current DB
   migration chain. Sydney EC2 `i-0cb44e7f2f15e2cd0` in
   `ap-southeast-2` is running and RDS `neuralshield-production-db`
   was available. In a read-only AWS audit, this instance was not available
   via Systems Manager, and no CodeDeploy/CodePipeline/ECS deployment route
   existed. Repository GitHub CI does not deploy production.
   Deploy behind `AGENCY_SAAS_WHOP_ENABLED=false` and
   `AGENCY_SAAS_WHOP_LIMITS_ENABLED=false`; verify schema migration and
   unaffected existing app and checkout before enabling.
7. **End-to-end commercial acceptance:** with an explicitly authorized
   controlled paid test, observe Whop paid transaction, merchant identity,
   approved price/plan, correct user/tenant access, correct workflow limits,
   duplicate delivery, failed renewal, cancellation/refund revocation,
   customer notification and preserved one-time products.
   Record transaction IDs privately, never payment credentials in GitHub.
8. **Publication:** only after steps 1–7 pass, verify store/product and
   checkout-link visibility, website CTA URLs, cancellation and terms pages,
   operational monitoring, support and rollback owner.

## Current development evidence

- Draft PR #17 `feature/agency-saas-whop-recurring-guardrails` includes:
  SQLAlchemy Whop tenant bindings and migration, provider-neutral
  authoritative snapshot guardrails, separate $19/$59/$149 plan allowlist,
  24-hour access freshness gate, bounded reconciliation library,
  provider-ownership claim protocol, replay-safe persistence, and
  separate one-time vs recurring payment classification.
- All of the above are **not** proof of production fulfilment until real Whop
  subscription API responses, authenticated ownership and endpoint
  wiring are independently tested.
- CI runs synthetic backend/frontend/PostgreSQL checks only. A green CI run
  must never automatically publish paid Whop links.

## Safe release order

1. Finish provider, ownership, event and reconciliation contract work in
   draft PR; use synthetic and isolated PostgreSQL CI to prevent regressions.
2. With authenticated Sydney deployment access, inspect currently deployed
   code and migration head, back up first, and prepare a rollback.
3. Deploy code/schema with all new recurring flags OFF; verify health and
   unchanged Agency one-time/Paddle paths.
4. Prove webhook authenticity and provider lookups against a real Whop
   controlled subscription. Establish exact tenant ownership and data flow.
5. Turn on the recurring handler and monitored reconciliation; verify all
   access grant/revoke paths. Only then enable new usage limits.
6. Perform controlled live acceptance and only then publish/advertise all
   three monthly paid plans. If any acceptance check fails, keep checkouts
   unpublished and flags OFF. Never destructively downgrade a populated
   subscription-binding table during rollback.

**Operator stop condition:** if a missing event, provider schema, proof
binding, deployment access or buyer acceptance check is not verified, release
status remains **NOT LIVE**. User approval to launch is granted; blockers
are engineering/production evidence, not missing user approval.

## Official membership contract checkpoint (2026-11-16)

Official source: https://docs.whop.com/api-reference/memberships/retrieve-membership.md
(versioned OpenAPI page, currently advertising `2026-11-14-1`). The current API
exposes authenticated `GET https://api.whop.com/api/v1/memberships/{id}`,
with bearer scope `member:basic:read`. The path identifier is a **`mem_`**
membership ID (or license key), NOT an assumed `sub_` subscription ID.
The documented response includes `user_id` (buyer, possibly null),
`variant_id` (`plan_`), `updated_at`, and `status`. Documented statuses:
`trialing`, `active`, `past_due`, `completed`, `canceled`,
`expired`, `unresolved`. The documentation says `past_due` is a
post-failure grace period, `completed` can be a one-time purchase, and
`canceled`/`expired` do not grant access.

**Integration mismatch requiring code review:** existing synthetic provider
facts use a generic `subscription_id` and `customer_id`; do not silently
map them to Whop `mem_` and `user_id`. First verify seller account,
product, plan price/interval, membership ownership, billing status, payment
and refund relationships from the complete pinned OpenAPI schema. A Whop
`user_id` alone is not a verified SaaS login/tenant authorization. Keep
provider adapter and public checkout OFF until this mapping is implemented
and covered by contract fixtures plus signed-event acceptance tests. This
checkpoint is **documentation only**, not proof of a working adapter.
