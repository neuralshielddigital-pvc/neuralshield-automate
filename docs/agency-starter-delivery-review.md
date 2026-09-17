# Agency Starter delivery review

Prepared 18 September 2026 for owner review. Repository implementation only;
not deployed and not an end-to-end production payment certification.

## Changes

The existing member portal displays whatever resources the backend returns for
an active product entitlement. Two Starter-only resources are added:

- `starter-read-first`: a current Starter-specific opening guide.
- `starter-download-pack`: a ZIP containing 37 original files plus that guide
  and a contents list (39 archive entries).

The three existing Starter templates remain available. Pro Communications,
Advanced Operations and Commercial License resources and pricing are unchanged.
No frontend change, new database table, migration or new environment variable is
required for the download pack. Authenticated downloads now carry private,
no-store cache headers and nosniff.

## Content decisions

All 41 recovered files matched the previously recovered source manifest hashes.
37 files are shipped unchanged. File counts include format variants, not distinct
templates. The new guide makes this explicit.

| Recovered files retained outside the buyer ZIP | Reason |
| --- | --- |
| Start Here Welcome and Product Map, DOCX and PDF | Describes the broader suite, including a five-workflow vault absent from this Starter recovery. Replaced by the Starter-specific opening guide. |
| TRN001 Quick Start and Workflow Walkthrough Scripts, DOCX and PDF | Recording scripts explicitly marked MP4 recording pending. No recorded videos are supplied or advertised. |

Other written guides reference the broader implementation process. The new guide
explains that only the enumerated files are included. It links current published
terms and refund policy, preserves the $27 one-time offer, separates the
$19/$59/$149 monthly Automation product, and grants no new commercial rights.
The recovery archive retains the original 41 files; it has not been overwritten.
No spreadsheet formulas or original PDF/Word/HTML contents were rewritten.

## Local verification

26 focused tests passed, including 11 new delivery cases, using an in-memory
SQLite database, synthetic purchases and local HTTP test client requests.

Verified:

- Completed synthetic Starter transaction creates an entitlement; a signed
  member session lists and downloads the actual ZIP bytes.
- Every included source file matches its recorded SHA-256; the archive opens
  without CRC errors and its inventory matches its payload.
- A different buyer's Starter purchase cannot unlock the download for a buyer
  holding only Pro, Advanced or Commercial License.
- Missing/invalid/expired member credentials are rejected.
- Revoking an entitlement blocks downloads even for an existing member session.
- Unknown resources and missing pack files return 404.
- Existing Starter templates continue to download.

These tests do not exercise live Paddle, SMTP, PostgreSQL, AWS or a customer's
account. They create a synthetic member session directly; they do not prove the
email-link request/consume flow. Existing FastAPI/python-jose deprecation warnings
remain. No production email, purchase or deployment was performed.

Run from `backend` with the repository's development dependencies:

```sh
python -m pytest tests/test_agency_starter_delivery.py tests/test_agency_member_resources.py tests/test_agency_member_service.py tests/test_agency_commerce_service.py -q
```

## Automatic delivery follow-up

The original review identified missing customer-email enrichment and automatic
email dispatch. These are now implemented on this branch; see
[automatic delivery review](agency-automatic-delivery-review.md) for the current
behavior, tests, migration, disabled-by-default switch and remaining provider
acceptance requirements. The original 26-test evidence above describes the asset
integration alone, not the follow-up payment-to-access flow.

## Deployment review

Backend base commit: `3f0646920eea3482a7206a1efddbb656c5a622d1`.
Agency frontend inspected at `3f0b03c37122d5d182b574e40824469764298894`.

This backend repository also serves the Automation product. Deployment must be
reviewed against the current production revision and include rollback handling;
never replace production wholesale from this branch. The ZIP belongs under the
backend's existing resource directory and must not be copied into a public Nginx
web root. Download entitlement checks remain mandatory.

## Rebuild

From repository root:

```sh
python scripts/build_agency_starter_pack.py /path/to/agency-starter-recovery
```

The builder verifies all 41 source hashes before writing the 37-file buyer pack.
Only the whitelist is packaged; other files in the source directory are ignored.
The ZIP uses fixed timestamps for reproducibility.
