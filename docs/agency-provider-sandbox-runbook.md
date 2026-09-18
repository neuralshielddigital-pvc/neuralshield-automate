# Agency Starter: local provider sandbox preparation

## Owner-confirmed inputs and completed evidence

18 September 2026, owner-provided screenshots and text:

- The owner has only the live Agency website, not an existing staging website.
- Windows Docker Linux engine and Compose are available.
- Commit `318903a6d4cdb6acf6ef47b53006200b1e540c20` was checked out and its offline
  validation image built successfully on the owner's PC.
- PostgreSQL **16.15**, **39 passed, 8 warnings in 7.82 seconds**, test container
  exit code **0**. This is the automatic-delivery subset, not another 39 unique
  tests to add to the earlier 88-test count. Providers were fake/local.
- Both test containers were removed; `compose ps -a` showed no containers.
- Log export failed because two PowerShell commands were pasted onto one line.
  Evidence is the screenshots, not a successfully exported log or a run directly
  performed by the assistant. No repeat was requested merely to recreate logs.
- Sandbox Starter price is active, **USD 27, one-time**:
  `pri_01kzwq9m1s1m7ss5ds5exax1cb`.
- Owner approved `neuralshielddigital@gmail.com` for test purchase/delivery.

## Newly prepared harness

`ops/agency-provider-sandbox/` contains a separate local FastAPI harness, a sandbox
checkout page and a member page. It reuses the real commerce, signature, delivery
and member services. Production app routing, pricing and worker defaults are
unchanged. No production or cloud operation is part of this setup.

The API listens on host loopback port 8097 only. Its dedicated PostgreSQL database
has no host port, uses an internal Docker network, and keeps data in temporary
memory-backed storage. A separate API network permits sandbox Paddle and SMTP
outbound connections when the test is armed. The default is unarmed.

Only the configured sandbox price is accepted, and only one distinct completed
order is imported per database lifetime. Other events/prices are ignored instead
of being dispatched to the Automation product. Duplicate notifications reuse the
same order. Delivery checks Paddle's authenticated customer record against the
exact approved recipient. No manual resend route is exposed. A wrong-recipient
first order will block this bounded run rather than silently emailing someone else.

The one-order limit is a local harness limit; it does not prevent someone creating
additional transactions directly in Paddle. Restarting the database destroys the
test order and resets this limit, so keep it running until evidence is captured.

Member links point to `http://localhost:8097/member/` and must be opened on the
same PC. The member page loads no external scripts, removes the link token from
the address bar, holds the member token only in memory, and uses bearer-protected
downloads. Uvicorn access logging is disabled to avoid logging email-link tokens.
This is an operator test page, not a replacement for the production member UI.

Local verification: **51 passed, 7 warnings in 2.76 seconds** for the existing
39 automatic-delivery tests plus 12 harness tests, using SQLite and injected fake
providers. Both inline browser scripts passed `node --check`. The new harness
Docker build/startup, browser acceptance, real Paddle webhook and external email
have **not** been run. Earlier PostgreSQL evidence applies to the preceding
offline validation setup, not automatically to this new harness.

## Start unarmed on the owner's PC

Use the review branch containing this runbook, in a local development checkout.
From repository root, run these individually and stop on an error:

```powershell
.\ops\agency-provider-sandbox\Initialize-Local.ps1
docker compose -f ops/agency-provider-sandbox/compose.yaml config --quiet
docker compose -f ops/agency-provider-sandbox/compose.yaml build api
docker compose -f ops/agency-provider-sandbox/compose.yaml up -d
```

The initialization script creates the ignored `sandbox.env`, generates a random
session signing key locally, refuses to overwrite an existing file and prints no
credentials. It has not been executed in PowerShell by the assistant. Keep that
file private; the dedicated Docker build allowlist excludes it.

Open `http://localhost:8097/health`: expect `environment: sandbox`, `armed: false`,
`orders: 0`. Open `http://localhost:8097/`: expect checkout disabled. No provider
or SMTP credentials are needed for this unarmed check, and no provider call is
made by startup. Do not print `docker compose config` without `--quiet` or share
`docker inspect` output after installing credentials, because they expose env values.

## Remaining configuration before arming

### 18 September owner-operated update

The owner fetched `ee530ba55e875b1e16d1244ac9bd91edbddba725` and successfully
ran `Initialize-Local.ps1`. The owner reports saving the sandbox client token,
a replacement API key named **Agency Local Sandbox Test 2**, and Hostinger SMTP
configuration locally. Screenshots showed only Customers Read and Transactions
Read selected for the test key. Revocation of the first unused test key was
requested but has not been confirmed. Credential values have not been inspected
or tested externally.

After starting Docker Desktop and retrying the build/start, the owner's browser
showed `{"environment":"sandbox","armed":false,"orders":0,"delivery":[]}` at
`http://localhost:8097/health`. This confirms local harness startup; it does not
prove API authentication, SMTP authentication or delivery.

A separate webhook relay is now prepared; see
[the relay runbook](agency-sandbox-webhook-relay.md). No tunnel is active.

1. In **Paddle Sandbox > Developer tools > Authentication**, prepare a sandbox
   client-side token (`test_...`) and a separate sandbox API key. For this harness,
   API access is limited to reading transactions and customers. No create/write
   privileges are used by the backend. Enter values in `sandbox.env` locally.
2. Arrange a **webhook-only** HTTPS forwarding target for the local
   `POST /api/paddle/webhook` route. The local relay is implemented and tested with
   synthetic requests; public tunnel activation is not yet approved or performed.
   Never publish port 8097 or tunnel the whole member/API service.
   Forward the original raw body and Paddle-Signature, rewriting Host to localhost.
3. Add a separate sandbox notification destination subscribing to
   `transaction.completed`, using that approved forwarding URL. Preserve existing
   notification destinations. Store its secret locally as `PADDLE_WEBHOOK_SECRET`.
4. Provide an approved SMTP sender on port 587 with STARTTLS and its credentials,
   if required. The recipient approval does not establish a working sender or
   provide SMTP access. This setup never reads production credentials.
5. For Paddle.js checkout, confirm the sandbox default payment-link setting is
   suitable for localhost testing. Record any prior value before changing shared
   sandbox account settings; do not alter the live account.
6. Only after these prerequisites, set `AGENCY_STARTER_DELIVERY_ENABLED=true` in
   the local private env file and recreate **api only**. Do not restart the database
   during the bounded test. Startup rejects live keys, production API/member URLs,
   a different recipient/price, unrelated databases and incomplete TLS SMTP config.

Use only Paddle's sandbox test card after the checkout shows Test Mode. Verify
Paddle's completed transaction and webhook delivery, local `/health` delivery
status, actual receipt in the approved inbox, one-time link consumption and ZIP
download. `email_submitted` alone proves SMTP submission, not inbox delivery.

No credential was requested in chat, no provider setting was changed, no real or
sandbox payment was made, and no external email was sent in preparation.

## Cleanup after the bounded run

Capture sanitized results before stopping the database. Disable only the newly
created sandbox webhook forwarding/destination, stop its forwarding process, then:

```powershell
docker compose -f ops/agency-provider-sandbox/compose.yaml down --volumes
docker compose -f ops/agency-provider-sandbox/compose.yaml ps -a
```

Remove the temporary credentials from the local private env file and revoke only
keys created specifically for this test when no longer needed. Local images/cache
remain. Do not publish the image because it contains the paid Starter ZIP.

Refund/chargeback reconciliation and production rollout readiness remain separate
release requirements. This sandbox harness does not complete them.

Sources: [Paddle sandbox](https://developer.paddle.com/sdks/sandbox/),
[overlay checkout and localhost](https://developer.paddle.com/build/checkout/build-overlay-checkout/),
[webhook signatures](https://developer.paddle.com/webhooks/about/signature-verification/).
