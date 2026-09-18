# Agency local sandbox webhook relay

## Prepared scope

This repository-only addition provides a dedicated relay on host loopback 8098.
It forwards only POST `/api/paddle/webhook`, with no query string, to the fixed
Docker destination `api:8097`, rewriting Host to `localhost`. All member, download,
checkout, status, documentation and other paths are rejected. No forwarding target
can be supplied by a caller. Raw request bytes and Paddle-Signature are preserved;
authorization, cookies and other caller headers are not forwarded.

The relay requires JSON, rejects encoded bodies and browser Origin requests,
limits streamed bodies to 1 MiB and body read time to five seconds, and limits
upstream socket waits to four seconds. Only sanitized status responses leave it.
Upstream redirects are not followed. Signature format is screened at the relay;
cryptographic signature and timestamp checks remain in the real backend service.
The one-order and exact-recipient restrictions remain in the sandbox harness.

The relay image contains only its source and Python dependencies. It has no
Paddle/SMTP credentials, database access or paid Starter package. Its Docker
network is internal, and its sole published port binds to 127.0.0.1. The existing
API additionally joins this internal network via a separate Compose override.
No access logging, Docker socket, host-network mode or privileged container is used.

## Verification and limits

40 tests passed (28 new relay cases plus 12 existing harness cases), five warnings,
in 0.37 seconds. These use synthetic in-process requests and fake transport.
They check blocked paths/methods, query and encoded-path rejection, raw-body
preservation, exact transport target/Host, header isolation, body bounds and
sanitized failure handling. No external endpoint, email or payment was contacted.

Relay image build, Compose merge/networking on the owner's Docker Desktop,
live forwarding, authentic webhook receipt and external email remain unverified.
The existing owner's health-page result applies to the base local harness only.

## Local preparation after fetching this checkpoint

Keep `AGENCY_STARTER_DELIVERY_ENABLED=false`. Run each command separately and stop
on error. The two configuration files must be supplied in the order below.

```powershell
docker compose -f ops/agency-provider-sandbox/compose.yaml -f ops/agency-provider-sandbox/compose.relay.yaml config --quiet
docker compose -f ops/agency-provider-sandbox/compose.yaml -f ops/agency-provider-sandbox/compose.relay.yaml build webhook-relay
docker compose -f ops/agency-provider-sandbox/compose.yaml -f ops/agency-provider-sandbox/compose.relay.yaml up -d --no-deps api webhook-relay
```

This recreates the API with its saved local settings and added relay network but
does not restart the dedicated database. Inspect local `/health` on port 8097:
require sandbox, armed false, orders zero before continuing.

Verify these on the owner PC before any tunnel:

- GET `http://localhost:8098/health` returns 404.
- GET `http://localhost:8098/member/` returns 404.
- POST `http://localhost:8098/api/paddle/webhook` with JSON but no signature returns 401.
- A synthetic correctly-shaped signature reaches the unarmed backend and returns
  503. Do not arm merely to change this result; the synthetic signature is not valid.

## Concrete external proposal, pending owner approval

Use one free temporary Cloudflare Quick Tunnel, targeting only
`http://localhost:8098`, with a generated `trycloudflare.com` hostname. Cloudflare
proxies the test webhook body, including test customer details and transaction
metadata. This is a third-party public connection, not a deployment of the app.
It requires no changes to the company's DNS or AWS resources. Quick Tunnels are
for development/testing, with no uptime guarantee. The owner must agree to the
software/service terms when installing or using cloudflared.

After approval and local relay checks, run cloudflared on the owner PC:

```powershell
cloudflared tunnel --url http://localhost:8098
```

Do not point it at 8097. Check the public URL rejects `/health`, `/member/`, and
unsigned webhook posts before adding a separate Paddle SANDBOX notification
destination for `transaction.completed` at `https://GENERATED-HOST/api/paddle/webhook`.
Do not alter existing notification destinations. Put the new destination's secret
only in the local `sandbox.env`. Hostinger SMTP and Paddle API credentials stay
in the backend container; they are not given to Cloudflare or the relay.

Creating the tunnel/destination is separate from arming delivery. Complete the
base runbook's payment-link, credential and sender readiness first, then obtain
the bounded test go-ahead before enabling one test purchase/delivery to
`neuralshielddigital@gmail.com`. No real card or live Paddle account is used.

## Stop and cleanup

Stop the foreground cloudflared process with Ctrl+C after the bounded test. Disable
or delete only the newly created sandbox notification destination. Capture
sanitized evidence, then use both Compose files for cleanup:

```powershell
docker compose -f ops/agency-provider-sandbox/compose.yaml -f ops/agency-provider-sandbox/compose.relay.yaml down --volumes
docker compose -f ops/agency-provider-sandbox/compose.yaml -f ops/agency-provider-sandbox/compose.relay.yaml ps -a
```

The database is temporary and its evidence disappears when it stops. Remove only
test-specific credentials after the run; do not revoke shared SMTP credentials or
unrelated API keys. Neither public connectivity nor provider changes occurred
while preparing this checkpoint.

Source verified 18 September 2026:
[Cloudflare Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/).
