# QA Checklist

Use this checklist before merging major SaaS releases and before production deploys.

## Signup

- Create a new tenant with a unique email.
- Confirm strong password validation rejects weak passwords.
- Confirm duplicate email signup returns a safe error.
- Confirm new user is `ADMIN` for the new tenant.

## Login

- Login with valid credentials.
- Confirm invalid credentials fail.
- Confirm `/api/auth/me` returns the current user and tenant.
- Confirm logout revokes refresh token.

## Billing

- Open `/dashboard/billing`.
- Confirm current subscription state renders.
- Confirm only Razorpay is visible in customer-facing billing.
- Confirm Starter is `$19/month`.
- Confirm Pro is `$59/month`.
- Confirm Business is `$149/month`.
- Confirm order amount is calculated server-side.
- Confirm checkout signature verification rejects invalid signatures.
- Confirm payment amount, currency, order, user, tenant, and plan are validated.
- Confirm uncaptured payments cannot activate subscriptions.
- Confirm duplicate payment IDs cannot activate another account or plan.
- Confirm successful payment creates one Payment record.
- Confirm successful payment activates the correct subscription.
- Confirm billing dashboard and usage limits update after activation.

## Razorpay Live Verification

- Confirm Razorpay account is fully activated.
- Confirm international payments are enabled if USD checkout is required.
- Install live Key ID and Secret only in backend `.env`.
- Set `RAZORPAY_CURRENCY` to the currency approved for the live account.
- Configure the live Razorpay webhook.
- Complete a controlled small real payment.
- Confirm signature verification passes.
- Confirm subscription, Payment record, usage limits, billing dashboard, and audit logs update.
- Confirm controlled refund and refund audit logging work.

## Affiliate

- Register as affiliate.
- Confirm referral code and referral link render.
- Sign up using `?ref=CODE`.
- Create an active paid subscription for referred user.
- Confirm commission is created once.
- Approve, reject, and mark paid from admin routes.

## Leads

- Create a lead manually.
- Search by name, email, and source.
- Confirm duplicate email per tenant is blocked.
- Move lead between pipeline stages.
- Edit notes and confirm `last_contacted_at` updates.
- Delete a lead.

## Public Lead Form

- Open `/lead-form`.
- Submit name, email, phone, and message.
- Confirm safe success response.
- Confirm duplicate public email does not leak existing lead state.
- Confirm message is stored in lead metadata.
- Confirm `NEW_LEAD` workflows trigger.

## Workflow Automation

- Create workflow with public webhook trigger.
- Trigger public webhook.
- Confirm workflow run is logged.
- Confirm `CREATE_LEAD` action creates or updates a CRM lead.
- Confirm `ADD_AUDIT_LOG` creates audit log entry.
- Confirm failed actions mark the run as `FAILED`.

## Email Action

- Configure SMTP environment variables.
- Create workflow with `SEND_EMAIL`.
- Trigger workflow with payload containing `email` and `name`.
- Confirm email is sent.
- Remove SMTP config and confirm workflow run fails with clear SMTP error.

## Admin Dashboard

- Login as `ADMIN` or `SUPER_ADMIN`.
- Open `/admin`.
- Confirm stats cards load.
- Confirm users, subscriptions, leads, workflows, workflow runs, commissions, and audit logs render.
- Login as normal `USER` and confirm redirect to `/dashboard`.
- Confirm password hashes, token hashes, and secrets are not visible.

## AWS Production Smoke Test

- Run `alembic upgrade head`.
- Create admin with `scripts/create_admin.py`.
- Start backend with systemd.
- Confirm `curl https://api.example.com/api/health` returns `status=ok` and `database=ok`.
- Confirm Nginx reverse proxy preserves host and forwarded headers.
- Confirm Certbot SSL certificate is active.
- Confirm frontend can login against production API.
- Submit public lead form.
- Complete a controlled Razorpay payment verification.
- Check backend logs with `journalctl -u neuralshield-backend -f`.
- Restart backend and Nginx and confirm service recovery.
