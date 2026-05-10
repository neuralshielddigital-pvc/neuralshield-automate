import { apiRequest } from "@/lib/api";
import type { AffiliateCommission, AffiliateMeResponse, AffiliateReferral, AffiliateStats } from "@/lib/types";

export async function registerAffiliate() {
  return apiRequest<AffiliateMeResponse>("/api/affiliate/register", {
    method: "POST"
  });
}

export async function getAffiliateMe() {
  return apiRequest<AffiliateMeResponse>("/api/affiliate/me");
}

export async function getAffiliateReferrals() {
  return apiRequest<AffiliateReferral[]>("/api/affiliate/referrals");
}

export async function getAffiliateCommissions() {
  return apiRequest<AffiliateCommission[]>("/api/affiliate/commissions");
}

export async function getAffiliateStats() {
  return apiRequest<AffiliateStats>("/api/affiliate/stats");
}
