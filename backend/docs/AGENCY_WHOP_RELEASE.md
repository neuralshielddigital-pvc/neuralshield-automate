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

Also provision AGENCY_WHOP_API_KEY (payment:basic:read and plan:basic:read only) and AGENCY_WHOP_WEBHOOK_SECRET. No payout, refund-write or transfer permission is needed.

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
