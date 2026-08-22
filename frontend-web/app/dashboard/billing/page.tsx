"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getPaddleInstance, initializePaddle } from "@paddle/paddle-js";
import { ApiError } from "@/lib/api";
import {
  createPaddleCheckout,
  getSubscription,
} from "@/lib/billing";
import type { Subscription } from "@/lib/types";

type Plan = {
  name: "Starter" | "Pro" | "Enterprise";
  displayName: "Starter" | "Pro" | "Business";
  price: number;
  note: string;
  badge: string;
  features: string[];
};

const plans: Plan[] = [
  {
    name: "Starter",
    displayName: "Starter",
    price: 19,
    note:
      "Perfect for solo founders and small businesses starting their automation journey.",
    badge: "",
    features: [
      "10 Active Workflows",
      "500 Automation Runs / Month",
      "Unlimited Webhooks",
      "Gmail, Slack & Google Sheets",
      "AI Workflow Actions",
      "Workflow Template Marketplace",
      "Email Support",
    ],
  },
  {
    name: "Pro",
    displayName: "Pro",
    price: 59,
    note:
      "Ideal for growing teams that need powerful automation at scale.",
    badge: "Most Popular",
    features: [
      "50 Active Workflows",
      "20,000 Automation Runs / Month",
      "Everything in Starter",
      "Premium Workflow Templates",
      "API Access",
      "Priority Support",
      "Advanced AI Automation",
    ],
  },
  {
    name: "Enterprise",
    displayName: "Business",
    price: 149,
    note:
      "Built for businesses that need team collaboration and higher automation limits.",
    badge: "",
    features: [
      "Unlimited Active Workflows",
      "100,000 Automation Runs / Month",
      "Everything in Pro",
      "Team Access",
      "Advanced Analytics",
      "API Access",
      "Dedicated Onboarding",
    ],
  },
];

const activeSubscriptionStatuses = new Set([
  "ACTIVE",
  "TRIALING",
  "TRIAL",
  "PAID",
]);

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.detail || fallback;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

function formatSubscriptionStatus(status?: string | null): string {
  if (!status) {
    return "Inactive";
  }

  return status
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [checkoutPlan, setCheckoutPlan] = useState<Plan["name"] | null>(null);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const loadSubscription = useCallback(async (showRefreshState = false) => {
    if (showRefreshState) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const response = await getSubscription();
      setSubscription(response.subscription);
    } catch (loadError) {
      setError(
        getErrorMessage(loadError, "Could not load your subscription details."),
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadSubscription();
  }, [loadSubscription]);

  const currentPlanName =
    subscription?.plan?.name?.trim().toLowerCase() ?? "";

  const subscriptionStatus =
    subscription?.status?.trim().toUpperCase() ?? "INACTIVE";

  const hasActiveSubscription =
    Boolean(subscription) &&
    activeSubscriptionStatuses.has(subscriptionStatus);

  const currentPlan = plans.find(
    (plan) => plan.name.toLowerCase() === currentPlanName,
  );

  const periodLabel = useMemo(() => {
    if (!subscription?.current_period_end) {
      return "Not available";
    }

    const date = new Date(subscription.current_period_end);

    if (Number.isNaN(date.getTime())) {
      return "Not available";
    }

    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
    }).format(date);
  }, [subscription?.current_period_end]);

  function getPlanActionLabel(plan: Plan): string {
    if (checkoutPlan === plan.name) {
      return "Opening secure checkout...";
    }

    if (
      hasActiveSubscription &&
      currentPlan?.name.toLowerCase() === plan.name.toLowerCase()
    ) {
      return "Current plan";
    }

    if (!hasActiveSubscription || !currentPlan) {
      return `Choose ${plan.displayName}`;
    }

    return "Contact support to change plan";
  }

  async function handleCheckout(plan: Plan) {
    const isCurrentActivePlan =
      hasActiveSubscription &&
      currentPlan?.name.toLowerCase() === plan.name.toLowerCase();

    if (isCurrentActivePlan || checkoutPlan !== null) {
      return;
    }

    setError("");
    setSuccess("");
    setCheckoutPlan(plan.name);

    try {
      const checkout = await createPaddleCheckout(plan.name);
      const clientToken =
        process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;

      if (!clientToken) {
        throw new Error("Paddle client-side token is not configured.");
      }

      const paddle =
        getPaddleInstance() ??
        (await initializePaddle({
          token: clientToken,
          environment:
            process.env.NEXT_PUBLIC_PADDLE_ENV === "sandbox"
              ? "sandbox"
              : "production",
          eventCallback(event) {
            if (event.name === "checkout.completed") {
              setSuccess(
                "Payment completed. Your subscription will update shortly.",
              );
              setCheckoutPlan(null);
              window.setTimeout(() => {
                void loadSubscription(true);
              }, 1500);
            }

            if (event.name === "checkout.closed") {
              setCheckoutPlan(null);
            }
          },
        }));

      if (!paddle) {
        throw new Error("Could not initialize Paddle checkout.");
      }

      paddle.Checkout.open({
        transactionId: checkout.transaction_id,
      });
    } catch (checkoutError) {
      setError(
        getErrorMessage(
          checkoutError,
          "Could not start secure checkout. Please try again.",
        ),
      );
      setCheckoutPlan(null);
    }
  }

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6 sm:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <p className="page-kicker">Billing</p>

            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Plans and subscription
            </h1>

            <p className="mt-2 text-sm leading-6 text-steel">
              Choose the plan that matches your automation volume. Prices are
              shown in USD. Global subscriptions, taxes and checkout are
              processed securely through Paddle.
            </p>
          </div>

          <button
            className="btn-secondary shrink-0"
            disabled={loading || refreshing || checkoutPlan !== null}
            onClick={() => void loadSubscription(true)}
            type="button"
          >
            {refreshing ? "Refreshing..." : "Refresh subscription"}
          </button>
        </div>

        <div
          aria-live="polite"
          className="mt-5 grid gap-3"
        >
          {success ? (
            <div className="alert-success" role="status">
              {success}
            </div>
          ) : null}

          {error ? (
            <div className="alert-error flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <span>{error}</span>

              <button
                className="text-sm font-semibold underline underline-offset-4"
                disabled={loading || refreshing}
                onClick={() => void loadSubscription(true)}
                type="button"
              >
                Try again
              </button>
            </div>
          ) : null}
        </div>

        <div className="mt-6 grid gap-4 rounded-xl border border-line bg-linen/80 p-4 sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-steel">
              Current plan
            </p>

            <p className="mt-1 text-sm font-semibold text-ink">
              {loading
                ? "Loading..."
                : subscription?.plan?.name?.toLowerCase() === "enterprise"
                  ? "Business"
                  : subscription?.plan?.name ?? "No active plan"}
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-steel">
              Subscription status
            </p>

            <div className="mt-1">
              {loading ? (
                <p className="text-sm font-semibold text-ink">Loading...</p>
              ) : (
                <span
                  className={
                    hasActiveSubscription
                      ? "status-pill border-pine/20 bg-mint text-pine"
                      : "status-pill border-line bg-white text-steel"
                  }
                >
                  {formatSubscriptionStatus(subscription?.status)}
                </span>
              )}
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-steel">
              Renews / ends
            </p>

            <p className="mt-1 text-sm font-semibold text-ink">
              {loading ? "Loading..." : periodLabel}
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-steel">
              Cancellation
            </p>

            <p className="mt-1 text-sm font-semibold text-ink">
              {loading
                ? "Loading..."
                : subscription?.cancel_at_period_end
                  ? "Cancels at period end"
                  : hasActiveSubscription
                    ? "Renews normally"
                    : "Not applicable"}
            </p>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-4">
          <p className="page-kicker">Pricing</p>

          <h2 className="mt-2 text-2xl font-semibold text-ink">
            Select the right plan
          </h2>

          <p className="mt-2 text-sm text-steel">
            Choose a plan to start securely with Paddle. Existing active
            subscriptions can change plans through support without duplicate billing.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {plans.map((plan) => {
            const isCurrent =
              hasActiveSubscription &&
              currentPlan?.name.toLowerCase() === plan.name.toLowerCase();

            const isCheckingOut = checkoutPlan === plan.name;
            const disableButton =
              loading ||
              checkoutPlan !== null ||
              hasActiveSubscription;

            return (
              <article
                className={`surface-card relative flex h-full flex-col p-6 transition ${
                  plan.badge
                    ? "border-pine/40 shadow-panel"
                    : "hover:-translate-y-1 hover:border-pine/25 hover:shadow-panel"
                }`}
                key={plan.name}
              >
                {plan.badge ? (
                  <span className="absolute right-5 top-5 rounded-full bg-pine px-3 py-1 text-xs font-semibold text-white">
                    {plan.badge}
                  </span>
                ) : null}

                <div className="pr-24">
                  <h3 className="text-lg font-semibold text-ink">
                    {plan.displayName}
                  </h3>

                  <p className="mt-2 min-h-12 text-sm leading-6 text-steel">
                    {plan.note}
                  </p>
                </div>

                <div className="mt-6 flex items-end gap-1">
                  <span className="text-4xl font-semibold text-ink">
                    ${plan.price}
                  </span>

                  <span className="pb-1 text-sm font-medium text-steel">
                    USD / month
                  </span>
                </div>

                <ul className="mt-6 grid flex-1 gap-3 text-sm text-steel">
                  {plan.features.map((feature) => (
                    <li className="flex gap-2" key={feature}>
                      <span
                        aria-hidden="true"
                        className="font-semibold text-pine"
                      >
                        ✓
                      </span>

                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  className={isCurrent ? "btn-secondary mt-7 w-full" : "btn-primary mt-7 w-full"}
                  disabled={disableButton}
                  onClick={() => void handleCheckout(plan)}
                  type="button"
                >
                  {isCheckingOut
                    ? "Opening secure checkout..."
                    : getPlanActionLabel(plan)}
                </button>

                {isCurrent ? (
                  <p className="mt-3 text-center text-xs text-steel">
                    This plan is already active. Duplicate payment is disabled.
                  </p>
                ) : hasActiveSubscription ? (
                  <p className="mt-3 text-center text-xs text-steel">
                    Contact support to change plans without duplicate billing.
                  </p>
                ) : (
                  <p className="mt-3 text-center text-xs text-steel">
                    Secure checkout. No payment is made until you confirm.
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
