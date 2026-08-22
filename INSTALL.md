# NeuralShieldDigital Paddle Billing

The active customer billing provider is Paddle.

Approved recurring monthly prices:

- Starter — USD 19/month
- Pro — USD 59/month
- Business — USD 149/month

## Active checkout flow

Authenticated customers start checkout from:

`https://app.neuralshielddigital.com/dashboard/billing`

The frontend requests a Paddle transaction from:

`POST /api/paddle/checkout`

The transaction is then opened with Paddle.js.

## Webhook

Backend webhook endpoint:

`https://api.neuralshielddigital.com/api/paddle/webhook`

Paddle webhook requests must use the configured `Paddle-Signature`
verification flow.

## Required backend configuration

- `PADDLE_API_KEY`
- `PADDLE_WEBHOOK_SECRET`
- `PADDLE_ENVIRONMENT`
- `PADDLE_API_BASE_URL`
- `PADDLE_CHECKOUT_URL`
- `PADDLE_STARTER_PRICE_ID`
- `PADDLE_PRO_PRICE_ID`
- `PADDLE_BUSINESS_PRICE_ID`

Production billing requires `PADDLE_ENVIRONMENT=production` and a Paddle
live API key.

## Required frontend configuration

- `NEXT_PUBLIC_PADDLE_CLIENT_TOKEN`
- `NEXT_PUBLIC_PADDLE_ENV`

## Compatibility note

Historical database columns and migrations may retain `stripe_*` names for
backwards-compatible schema history. Those names do not make Stripe an active
customer checkout provider and must not be renamed casually without a separate
database migration plan.

Plan changes for an existing active subscription are currently handled through
support to prevent duplicate subscriptions.
