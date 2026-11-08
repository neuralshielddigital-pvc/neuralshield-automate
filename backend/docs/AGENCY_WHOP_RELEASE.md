# Agency Whop release

Target: agency.neuralshielddigital.com only. Existing Workflow Automation billing and historical Paddle orders remain separate.

## Implemented

- POST /api/webhooks/agency/whop verifies raw-body HMAC and a five-minute replay window before processing.
- REST reads use https://api.whop.com/api/v1 and Api-Version-Date: 2026-11-07.
- Payment merchant, one-time variant, product, quantity, USD subtotal and amount collected before tax must agree.
- Only server-verified paid purchases create Agency orders, entitlements and member-portal fulfilments.
- Duplicate purchases remain idempotent; succeeded refunds revoke only that order's entitlements. Refund-before-success creates a revoked record; a delayed success cannot reactivate it.
- Existing authenticated member portal supplies tier-specific resources. Buyer requests a one-time email access link at /member/ using the checkout email. No automatic customer email is sent by the webhook.
- Browser redirects never grant access.

## Server configuration

Store secrets in the deployment's protected environment, never GitHub or browser JavaScript.

```
AGENCY_WHOP_ENABLED=false
AGENCY_WHOP_ACCOUNT_ID=biz_v89TqnjOiedw0z
AGENCY_WHOP_PRODUCT_STARTER_ID=prod_oZ4czrRLbgDMr
AGENCY_WHOP_PRODUCT_PRO_ID=prod_QdVCTHenFB31Y
AGENCY_WHOP_PRODUCT_ADVANCED_ID=prod_fOpMVDOWI6zz8
AGENCY_WHOP_PRODUCT_LICENSE_ID=prod_RwYu39afBgUKe
```

Also provision AGENCY_WHOP_API_KEY (payment:basic:read, plan:basic:read and member:email:read only) and AGENCY_WHOP_WEBHOOK_SECRET. No payout, refund-write or transfer permission is needed.

Create webhook version v1 with api_version_date 2026-11-07, URL https://api.neuralshielddigital.com/api/webhooks/agency/whop and events payment.succeeded, refund.created, refund.updated. Preserve the literal ws_ signing secret. Do not register an unimplemented endpoint in production.

## Deployment gate

1. Identify and verify the actual Agency backend server and deployed Git HEAD. Historical location: /home/ubuntu/apps/automate/backend; frontend /var/www/neuralshield-agency-pilot. No server connection was established in this session.
2. Back up existing frontend and protected runtime config. Review current migration head and the staged provider-identity migration before applying it. Never recreate or erase the database.
3. Install backend release and migration with Whop disabled. Confirm API/app health, legacy order access and protected downloads.
4. Provision minimal API key and signed webhook, enable backend, and verify provider delivery using an actual sandbox fixture. Dashboard sample payloads must not create live buyer entitlements unless independent provider lookup verifies them.
5. Deploy frontend PR only after backend verification succeeds; verify each hosted product's one-time USD price, return flow, paid buyer access, other-tier denial and refund revocation. Merchant products remain hidden until the complete flow is verified.
6. Live purchase or refund transactions require user execution/authorization. No real transaction was run in this session.

## Outstanding production evidence

Credentials, webhook provisioning, server deployment access, migration execution, SMTP delivery, real checkout/member download and refund lifecycle remain unverified. Passing synthetic tests is not evidence that the production rollout is complete. The readiness report deliberately remains false pending these checks.

## References

https://docs.whop.com/developer/guides/webhooks
https://docs.whop.com/api-reference/payments/retrieve-payment
https://api.whop.com/api/v1/openapi.json

## Server preflight on 2026-11-08

Confirmed Sydney neuralshield-server serves app/API and Agency. Live backend is not a Git checkout; do not use it as a development directory. Live migration head is 20260831_0003. Approved commit was cloned separately under /home/ubuntu/agency-whop-staging/. Separate Python 3.10 virtual environment created there; production dependencies were not changed. Initial isolated suite exposed three pre-existing tests importing datetime.UTC (3.11+); they now use timezone.utc, and CI covers Python 3.10/3.12. Runtime SMTP host/from settings are present, Whop credentials absent. Final migration and shared-backend rollback plan still require verification; no production code/schema or checkout switched.

## Credential provisioning verified 2026-11-08

User approved creating the Agency Billing Verification company API key and storing it on the Sydney server. It has exactly payment:basic:read, plan:basic:read and member:email:read; source IP allow-list is 54.206.33.106/32. The credential is saved outside source and production runtime in /home/ubuntu/.config/neuralshield/agency-whop.env, owner ubuntu, mode 0600, parent mode 0700. Whop remains disabled. No secret value is recorded here.

Authenticated server-origin GET /payments and GET /variants both returned HTTP 200. The provider variant listing independently confirmed all four products as one_time, currency usd, at 27/67/97/197. This does not verify a real buyer payment or delivery.

## Concrete production cutover scope (not executed)

Only the following backend files differ from the live verified baseline, plus new Agency Whop files: app/api/router.py (Agency router registration), app/core/config.py (Agency settings), app/models/agency_commerce.py (provider identity), app/services/agency_commerce_service.py (legacy Paddle writer compatibility). New files are app/api/routes/agency_whop.py, app/services/agency_whop_*.py and alembic/versions/20261028_0001_agency_provider_identity.py. Production dependencies match source requirements; no in-place dependency upgrade is planned.

Before any cutover: recheck live baseline hashes, current migration 20260831_0003, order invariants and backups; prepare a protected same-server backup of affected code and database. Reject drift. The running directory is never a development checkout.

The provider-identity migration adds required non-null fields. The old Agency Paddle writer does not populate them. Therefore migration and the compatible writer must ship together while the shared backend is stopped; a brief app/API interruption is expected. This requires specific approval and a planned maintenance window. Do not migrate while the old writer can receive traffic.

After installing the exact reviewed artifact, configure the protected environment, restart only neuralshield-backend.service and verify existing app/API/Agency endpoints and protected downloads. Other services are excluded. Register the Agency webhook at https://api.neuralshielddigital.com/api/webhooks/agency/whop for payment.succeeded, refund.created, refund.updated on v1/date 2026-11-07; store its signing secret in the same protected server configuration. New webhook credential provisioning also requires approval. Verify real provider delivery before switching the website's checkout.

Rollback before any Whop orders: restore protected affected-file backup and downgrade only after confirming no non-Paddle orders. After a Whop order exists, never downgrade/drop provider columns or restore the incompatible old writer; disable Whop/new checkout, retain the compatible schema/writer, and preserve all purchase history for recovery. Frontend rollback can restore its own backup without deleting billing records.

Production deployment, migration, shared service restart, webhook registration and checkout switching have not been approved in this credential-provisioning step and were not executed. A real purchase/refund must be performed by the user when needed for final acceptance. Hidden products stay hidden until acceptance.


## Latest approved deployment checkpoint — 2026-11-08 14:00 UTC

This section supersedes the earlier preflight and not-executed statements above. The user explicitly approved backup, Agency migration, coordinated shared-backend restart, webhook setup and checkout switching only after verification. This approval does not authorize the assistant to perform a real charge/refund.

Observed completed work:

- Created Whop webhook hook_aBUrUkwdF7CjU, named Agency Whop Billing, for https://api.neuralshielddigital.com/api/webhooks/agency/whop; version v1/date 2026-11-07; exactly payment.succeeded, refund.created and refund.updated. Its last observed state is Disabled (paused).
- Stored its signing secret in the existing protected server configuration, without recording secret values here. The API key remains restricted to read payments/plans/member emails and server IP 54.206.33.106/32.
- A first pg_dump attempt failed because the CLI was not receiving the existing RDS TLS root certificate parameter. The second runner preserved sslrootcert/sslcert/sslkey parameters and verification; no TLS checks were disabled.
- Validated PostgreSQL 17 full-database custom archive with pg_restore --list. Backup directory: /home/ubuntu/.local/state/agency-whop-backups/20261108T135718Z; database.dump size 1104703 bytes at creation. The protected directory also contains affected-original-file backups, Agency frontend archive, original Agency environment and manifest. Files mode 0600/directories 0700.
- Installed exactly the 16 scoped backend/migration files from commit 95473db45cd9609697c6471493cd4d1e8bdf6930 after matching the live source to base 3f0646920eea3482a7206a1efddbb656c5a622d1. Applied migration 20261028_0001 and the compatible legacy Paddle writer together while only neuralshield-backend.service was stopped.
- Created the dedicated systemd drop-in /etc/systemd/system/neuralshield-backend.service.d/agency-whop.conf referencing the protected Agency environment file. Set AGENCY_WHOP_ENABLED=true and restarted that service. The deployment runner reported BACKEND_INSTALLED after service active, local /api/health HTTP 200 with database ok, unsigned webhook HTTP 400, and unauthenticated member resources HTTP 401.
- Deployment runner resides in the separate staging checkout as agency_release_v2.py; SHA-256 91afcd6764d8fb9605e9a06d17490f1bc99bf2cc25d27072dc6c1194a2dbf681. Staging directory remains /home/ubuntu/agency-whop-staging/6b7aa02870930e64f9ae7afaa78b2e054040b737; its source HEAD is 95473db. Do not rerun its one-time apply action on the now-migrated server.

Verified CI evidence (read the run directly, not only PR-filtered lists): https://github.com/neuralshielddigital-pvc/neuralshield-automate/actions/runs/42460004275 completed successfully for exact commit 95473db45cd9609697c6471493cd4d1e8bdf6930. Staging suite was 119 passed, 3 skipped; CI includes Python 3.10/3.12 and PostgreSQL checks. An empty filtered connector response must not erase this direct-run evidence.

Interruption and remaining work:

The subsequent browser call was rejected by automatic approval review because of an account usage limit while opening the Whop hosted checkout. It was a review/usage failure, not a determination that the action was unsafe. Do not bypass the blocked action through another browser, raw CDP, terminal network execution or another transport. User must resolve the browser usage/credit gate before those browser actions resume.

The same tool call had attempted to submit an external signed no-grant preflight and app/API/site health command through the existing SSH terminal before the Whop navigation rejection. Its output has not been observed, so do not claim those external checks passed; inspect the terminal state after access is restored.

Website checkout has NOT been switched. Whop webhook last observed paused. No real purchase/refund, buyer SMTP delivery, paid member download or refund-revocation acceptance test was completed. Hidden products remain hidden. Frontend release candidate is commit 33b4082deda5921f1bae50b0b30076886e8add68 in PR #10; its index.html, checkout.js and checkout-config.js were independently compared with the local deployment bundle and matched. The bundle was prepared locally but not transferred/deployed.

Resume by reading current server migration/service state and Whop webhook state before making any changes; preserve the existing full backup and all purchase history. Complete provider delivery/hosted checkout verification, then enable the approved webhook and switch only the exact Agency frontend files after gates pass. Do not repeat backup/migration/key creation or claim the launch is complete. Real financial acceptance actions require user handoff.
