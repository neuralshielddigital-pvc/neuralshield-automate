import { apiRequest } from "@/lib/api";
import type { SubscriptionResponse } from "@/lib/types";

export async function getSubscription() {
  return apiRequest<SubscriptionResponse>("/api/billing/subscription");
}

export async function createCheckoutSession(planName: string) {
  return apiRequest<{ checkout_url: string }>("/api/billing/create-checkout-session", {
    method: "POST",
    body: JSON.stringify({ plan_name: planName })
  });
}
