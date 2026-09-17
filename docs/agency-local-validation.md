# Agency local PostgreSQL validation

**Later owner-operated result:** the pinned setup was built on Windows and passed
39 tests on PostgreSQL 16.15, with 8 warnings in 7.82 seconds and container exit
code 0. Container cleanup was confirmed in screenshots. See
`agency-provider-sandbox-runbook.md` for evidence limits and the next test stage.
The preparation notes below describe the state before that owner-operated run.

The owner confirmed that only the live website exists. This prepared local test
option does not require a new cloud server. It is not a staging website and does
not yet test a real Paddle checkout. Never run these commands on the live server.

## Prepared, not executed

Docker is unavailable in the assistant runtime. YAML and source paths were checked;
the image build, Compose startup and actual PostgreSQL tests remain unverified.
The prior 88 passing tests used SQLite and local/mock providers. This file adds no
new PostgreSQL pass claim. PostgreSQL 16 is a provisional test baseline; confirm
the deployed major version before using the result as deployment evidence.

## What the setup does

- Builds a Python 3.12 test image from selected repository files. The dedicated
  build-context allowlist excludes environment files, Git history and frontend.
- Runs a new PostgreSQL container with memory-backed disposable storage. There
  are no published ports, production mounts or existing-database connections.
- Gives the test role schema creation rights in the dedicated test database,
  without superuser, role creation, database creation or replication privileges.
- Shares the PostgreSQL container's network namespace with the tests. PostgreSQL
  has `network_mode: none`; tests can use loopback PostgreSQL/SMTP but have no
  external network interface. Image downloads and dependency installation occur
  during preparation, before this isolated test runtime.
- Runs the existing guarded database runner. Paddle remains fake; SMTP is fake or
  a loopback-only receiver. This is not real payment or external-email acceptance.

The credentials in these files are deliberately public synthetic fixture values.
Do not replace them with production credentials. The app image contains the paid
Starter package: keep it local/private and do not publish it to an image registry.

## Local operator steps

Prerequisite: Docker with Compose v2, using Linux containers on a local development
computer. Check availability with `docker version` and `docker compose version`.
Use a fresh checkout of `feature/agency-starter-delivery-20260918`. Run from its
repository root, using the exact Compose file below. No `.env` is required.

```powershell
docker compose -f ops/agency-local-validation/compose.yaml config --quiet
docker compose -f ops/agency-local-validation/compose.yaml build tests
docker compose -f ops/agency-local-validation/compose.yaml up --abort-on-container-exit --exit-code-from tests
```

Record the test exit code and test summary before cleanup. Exit code zero and no
failing tests are required; a successful build alone is not a passing test run.
If a container/build fails, retain its error output for diagnosis and do not retry
against production. Cleanup only this dedicated Compose project:

```powershell
docker compose -f ops/agency-local-validation/compose.yaml down --volumes
docker compose -f ops/agency-local-validation/compose.yaml ps -a
```

The final command should show no project containers. Test database contents vanish
when its container stops. Local build images/cache remain; no cloud resources are
created. Avoid generic Docker prune commands because they affect other projects.

## After a passing local run

Real provider validation still needs a separate approved sandbox API/member portal
target, Paddle sandbox product/key/webhook configuration and an approved recipient.
Do not expose this offline Compose setup to the internet or reuse its fixture
passwords for staging. Consult `agency-provider-validation-readiness.md` for the
remaining provider requirements and refund/chargeback release gap.

References: [Compose service networking](https://docs.docker.com/reference/compose-file/services/#network_mode)
and [Docker build-context exclusion](https://docs.docker.com/build/concepts/context/#dockerignore-files).
