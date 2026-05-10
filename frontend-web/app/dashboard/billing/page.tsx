"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError } from "@/lib/api";
import { createCheckoutSession, getSubscription } from "@/lib/billing";
import type { Subscription } from "@/lib/types";

const plans = [
  { name: "Starter", price: "$29", note: "For early launch workspaces" },
  { name: "Pro", price: "$99", note: "For growing automation teams" },
  { name: "Enterprise", price: "Custom", note: "For advanced SaaS operations" }
];

export default function BillingPage() {
  const searchParams = useSearchParams();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutPlan, setCheckoutPlan] = useState<string | null>(null);
  const [error, setError] = useState("");

  const success = searchParams.get("success") === "true";

  useEffect(() => {
    getSubscription()
      .then((response) => setSubscription(response.subscription))
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Could not load subscription."))
      .finally(() => setLoading(false));
  }, []);

  const periodLabel = useMemo(() => {
    if (!subscription?.current_period_end) return "Not available";
    return new Intl.DateTimeFormat("en", {
      dateStyle: "medium"
    }).format(new Date(subscription.current_period_end));
  }, [subscription]);

  async function handleCheckout(planName: string) {
    setError("");
    setCheckoutPlan(planName);
    try {
      const response = await createCheckoutSession(planName);
      window.location.href = response.checkout_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not start Stripe checkout.");
      setCheckoutPlan(null);
    }
  }

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6 sm:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="page-kicker">Billing</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Subscription</h1>
            <p className="mt-2 text-sm leading-6 text-steel">
              Manage plans, payment status, and subscription renewals through Stripe Checkout.
            </p>
          </div>
          {success ? (
            <div className="alert-success max-w-md">
              Payment successful. Your subscription will update as soon as the Stripe webhook is processed.
            </div>
          ) : null}
        </div>

        <div className="mt-6 grid gap-4 rounded-xl border border-line bg-linen/80 p-4 sm:grid-cols-4">
          <div>
            <p className="text-xs font-semibold uppercase text-steel">Plan</p>
            <p className="mt-1 text-sm font-semibold text-ink">
              {loading ? "Loading..." : subscription?.plan.name ?? "No active plan"}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-steel">Status</p>
            <p className="mt-1 text-sm font-semibold text-ink">{subscription?.status ?? "INACTIVE"}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-steel">Renews / Ends</p>
            <p className="mt-1 text-sm font-semibold text-ink">{periodLabel}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-steel">Cancel at period end</p>
            <p className="mt-1 text-sm font-semibold text-ink">
              {subscription?.cancel_at_period_end ? "Yes" : "No"}
            </p>
          </div>
        </div>
      </section>

      {error ? <p className="alert-error">{error}</p> : null}

      <section className="grid gap-4 lg:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = subscription?.plan.name?.toLowerCase() === plan.name.toLowerCase();
          return (
            <div className="surface-card p-6 transition hover:-translate-y-1 hover:border-pine/25 hover:shadow-panel" key={plan.name}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-ink">{plan.name}</h2>
                  <p className="mt-2 text-sm leading-6 text-steel">{plan.note}</p>
                </div>
                {isCurrent ? (
                  <span className="status-pill border-pine/20 bg-mint text-pine">Current</span>
                ) : null}
              </div>
              <p className="mt-6 text-3xl font-semibold text-ink">{plan.price}</p>
              <button
                className="btn-primary mt-6 w-full"
                disabled={checkoutPlan !== null}
                onClick={() => handleCheckout(plan.name)}
                type="button"
              >
                {checkoutPlan === plan.name ? "Redirecting..." : isCurrent ? "Manage with Checkout" : `Choose ${plan.name}`}
              </button>
            </div>
          );
        })}
      </section>
    </div>
  );
}
