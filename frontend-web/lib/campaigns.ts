import { apiRequest } from "@/lib/api";
import type {
  Campaign,
  CampaignListResponse,
  CampaignStats,
  CampaignType,
  LeadImportResponse,
  LeadListResponse,
  Workflow,
  WorkflowListResponse
} from "@/lib/types";

export type CampaignPayload = {
  name: string;
  type: CampaignType;
  subject?: string | null;
  message: string;
};

export type LeadImportPayload = {
  leads: Array<{
    name?: string | null;
    email: string;
    phone?: string | null;
    tags: string[];
  }>;
};

export async function getCampaignStats() {
  return apiRequest<CampaignStats>("/api/campaigns/stats");
}

export async function getCampaigns() {
  return apiRequest<CampaignListResponse>("/api/campaigns");
}

export async function createCampaign(payload: CampaignPayload) {
  return apiRequest<Campaign>("/api/campaigns", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateCampaign(campaignId: string, payload: Partial<CampaignPayload>) {
  return apiRequest<Campaign>(`/api/campaigns/${campaignId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function deleteCampaign(campaignId: string) {
  return apiRequest<void>(`/api/campaigns/${campaignId}`, {
    method: "DELETE"
  });
}

export async function activateCampaign(campaignId: string) {
  return apiRequest<Campaign>(`/api/campaigns/${campaignId}/activate`, {
    method: "POST"
  });
}

export async function pauseCampaign(campaignId: string) {
  return apiRequest<Campaign>(`/api/campaigns/${campaignId}/pause`, {
    method: "POST"
  });
}

export async function getLeads() {
  return apiRequest<LeadListResponse>("/api/leads");
}

export async function importLeads(payload: LeadImportPayload) {
  return apiRequest<LeadImportResponse>("/api/leads/import", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getWorkflows() {
  return apiRequest<WorkflowListResponse>("/api/workflows");
}

export async function createWorkflow(payload: { name: string; is_active: boolean; definition: Record<string, unknown> }) {
  return apiRequest<Workflow>("/api/workflows", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
