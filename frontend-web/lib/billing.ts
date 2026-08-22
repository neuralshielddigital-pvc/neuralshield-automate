import { apiRequest } from "@/lib/api";
import type { SubscriptionResponse } from "@/lib/types";

export async function getSubscription() {
  return apiRequest<SubscriptionResponse>(
    "/api/billing/subscription",
  );
}

export async function createPaddleCheckout(
  planName: string,
) {
  return apiRequest<{
    transaction_id: string;
    provider: "paddle";
    plan: string;
    environment: string;
  }>("/api/paddle/checkout", {
    method: "POST",
    body: JSON.stringify({
      plan_name: planName,
    }),
  });
}
