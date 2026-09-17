# Agency provider-validation readiness

18 September 2026. This checkpoint adds sandbox separation and a guarded
PostgreSQL runner. It does not certify PostgreSQL or real Paddle acceptance.

## Evidence from this checkpoint

88 focused tests passed, with 23 dependency deprecation warnings, in 3.04 seconds.
The new SMTP test uses the real application EmailService and Python SMTP client
against a temporary receiver bound to 127.0.0.1. It verifies the received message,
consumes its one-time link through the member API and downloads the protected ZIP.
The receiver relays nothing to the internet and is shut down after the test.
Paddle responses remain test doubles, and normal database tests use SQLite.

This proves local SMTP protocol handling, not external SMTP credentials, TLS,
DKIM/SPF, inbox placement or real customer receipt. No external email was sent.

## PostgreSQL execution blocked here

No PostgreSQL server/client or Docker is present in the current runtime.
The package-manager attempt failed because the runtime disallows the user/group
switches it requires. No attempt was made to bypass that restriction. No
PostgreSQL server was started, no database connection was made and no PostgreSQL
integration pass is claimed.

`scripts/run_agency_postgres_validation.py` is prepared for a separately approved
local PostgreSQL test environment. It refuses non-loopback hosts, non-test database
names, query-parameter overrides and missing explicit confirmation before trying
to connect. Each database-using test creates a unique schema, uses it for its
fixtures, and drops only that schema in cleanup. It does not create, reset or drop
an existing database. Normal test fixtures remain SQLite by default.

The runner exercises the same signed-payment, delivery, link, download and
competing-worker tests plus a migration downgrade/upgrade round-trip. Actual
PostgreSQL execution remains unverified until it runs successfully there.

Setup requirements for the approved test operator:

1. Provision a dedicated, empty local PostgreSQL database whose name starts with
   `nsd_agency_test_`. Use a dedicated role with schema creation rights only in that
   test database, and the same PostgreSQL major version intended for deployment.
2. Install the repository's `backend/requirements-dev.txt` in a test virtualenv.
3. Set `AGENCY_TEST_DATABASE_URL` securely in that shell to the dedicated
   `postgresql+psycopg` URL, using host `127.0.0.1` or `::1`. Do not paste it in chat.
4. Set `AGENCY_TEST_ALLOW_ISOLATED_POSTGRES=yes` in that test shell.
5. Run `python scripts/run_agency_postgres_validation.py` from repository root.
6. Confirm successful tests and no leftover `nsd_agency_test_` schemas. Interrupted
   processes may leave their uniquely named schemas for operator cleanup; never
   delete schemas outside this run's recorded scope.

The runner disables both application background workers. The tests inject fake
Paddle providers, fake SMTP or a loopback-only receiver. No live provider
credentials are needed to run this PostgreSQL validation.

## Sandbox configuration implemented

| Setting | Required value for a real sandbox test |
| --- | --- |
| PADDLE_ENVIRONMENT | sandbox |
| PADDLE_API_BASE_URL | https://sandbox-api.paddle.com |
| PADDLE_API_KEY | Sandbox credential, supplied securely at runtime |
| PADDLE_WEBHOOK_SECRET | Secret for the sandbox notification destination, supplied securely |
| AGENCY_STARTER_SANDBOX_PRICE_ID | Actual sandbox price ID for $27 USD, one-time Starter |
| AGENCY_DELIVERY_TEST_RECIPIENT | One owner-approved email address |
| AGENCY_MEMBER_BASE_URL | Approved test member portal URL, separate from production |
| AGENCY_STARTER_DELIVERY_ENABLED | false during setup; enable only for the bounded approved test |

Production's four approved price IDs and amounts are unchanged. In sandbox only
the explicitly configured Starter price is accepted; an empty, malformed or known
production price ID does not activate a sandbox catalog. Production never adopts
the sandbox price. The automated sandbox sender checks the exact allowed recipient
and rejects the production Agency/Automation member hosts. The member-email helper
also rejects a sandbox link pointing at those hosts. Manual sandbox access
requests are limited to the configured test recipient.

Sandbox products, keys and webhook destinations are distinct from live Paddle.
Official source: https://developer.paddle.com/sdks/sandbox/

## Missing for real provider validation

- An owner-approved isolated database and API/member-portal test target.
- Access to the owner's Paddle sandbox setup and its actual Starter price ID.
- Sandbox credentials installed securely in that test target.
- An approved external SMTP sender and owner-controlled recipient for a bounded
  real-email test, if external SMTP validation is desired after loopback tests.
- A separately configured test frontend pointing to the test API, plus a sandbox
  notification destination reaching the test API. The production member frontend
  still points to the production API and must not be used for sandbox access tokens.

No provider configuration, account connection, cloud resources, domain changes,
real email or real payment has been performed. These missing pieces must be
resolved before a real sandbox run, then before production activation. Refund and
chargeback reconciliation remain outside the current implementation and are still
a release-readiness requirement.
