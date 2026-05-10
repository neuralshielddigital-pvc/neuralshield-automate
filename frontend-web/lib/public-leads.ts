import { apiRequest } from "@/lib/api";

export type PublicLeadPayload = {
  tenant_slug: string;
  name?: string | null;
  email: string;
  phone?: string | null;
  source?: string | null;
  message?: string | null;
};

export type PublicLeadResponse = {
  success: boolean;
  message: string;
};

export async function submitPublicLead(payload: PublicLeadPayload) {
  return apiRequest<PublicLeadResponse>("/api/public/leads", {
    method: "POST",
    auth: false,
    body: JSON.stringify(payload)
  });
}
