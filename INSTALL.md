# NeuralShieldDigital Lemon Squeezy Billing

This change set replaces the active Razorpay customer checkout with Lemon
Squeezy recurring subscriptions while preserving historical Razorpay code and
database compatibility.

Approved monthly prices:

- Starter: USD 19
- Pro: USD 59
- Business: USD 149

The existing `stripe_*` database column names remain unchanged for backwards
compatibility. Lemon Squeezy provider identifiers are stored with a
`lemonsqueezy:` prefix.

Required environment variables:

- `LEMON_SQUEEZY_API_KEY`
- `LEMON_SQUEEZY_WEBHOOK_SECRET`
- `LEMON_SQUEEZY_STORE_ID`
- `LEMON_SQUEEZY_TEST_MODE`
- `LEMON_SQUEEZY_STARTER_PRODUCT_ID`
- `LEMON_SQUEEZY_STARTER_VARIANT_ID`
- `LEMON_SQUEEZY_PRO_PRODUCT_ID`
- `LEMON_SQUEEZY_PRO_VARIANT_ID`
- `LEMON_SQUEEZY_BUSINESS_PRODUCT_ID`
- `LEMON_SQUEEZY_BUSINESS_VARIANT_ID`

Webhook URL:

`https://api.neuralshielddigital.com/api/lemonsqueezy/webhook`

Required test and live webhook events:

- `order_created`
- `order_refunded`
- `subscription_created`
- `subscription_updated`
- `subscription_cancelled`
- `subscription_resumed`
- `subscription_expired`
- `subscription_paused`
- `subscription_unpaused`
- `subscription_plan_changed`
- `subscription_payment_failed`
- `subscription_payment_success`
- `subscription_payment_recovered`
