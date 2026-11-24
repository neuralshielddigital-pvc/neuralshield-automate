import { apiRequest } from "@/lib/api";
import type { SubscriptionResponse } from "@/lib/types";

export async function getSubscription() {
  return apiRequest<SubscriptionResponse>(
    "/api/billing/subscription",
  );
}

export async function createWhopCheckout(planName: string, commandId: string) {
  return apiRequest<{ checkout_url: string; provider: "whop" }>("/api/whop/checkout", {
    method: "POST",
    body: JSON.stringify({ plan_name: planName, command_id: commandId }),
  });
}

export async function refreshWhopSubscription() {
  return apiRequest<{ refreshed: boolean }>("/api/whop/refresh", { method: "POST" });
}
