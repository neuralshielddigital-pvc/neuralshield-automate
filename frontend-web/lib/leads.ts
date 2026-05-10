import { apiRequest } from "@/lib/api";
import type { Lead, LeadListResponse, LeadStage } from "@/lib/types";

export type LeadPayload = {
  name?: string | null;
  email: string;
  phone?: string | null;
  source?: string | null;
  tags: string[];
  metadata?: Record<string, unknown>;
};

export async function getLeads(search = "") {
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  return apiRequest<LeadListResponse>(`/api/leads${query}`);
}

export async function getLead(leadId: string) {
  return apiRequest<Lead>(`/api/leads/${leadId}`);
}

export async function createLead(payload: LeadPayload) {
  return apiRequest<Lead>("/api/leads", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateLead(leadId: string, payload: Partial<LeadPayload>) {
  return apiRequest<Lead>(`/api/leads/${leadId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function updateLeadStage(leadId: string, stage: LeadStage) {
  return apiRequest<Lead>(`/api/leads/${leadId}/stage`, {
    method: "PATCH",
    body: JSON.stringify({ stage })
  });
}

export async function updateLeadNotes(leadId: string, notes: string | null, lastContactedAt?: string | null) {
  return apiRequest<Lead>(`/api/leads/${leadId}/notes`, {
    method: "PATCH",
    body: JSON.stringify({ notes, last_contacted_at: lastContactedAt ?? null })
  });
}

export async function deleteLead(leadId: string) {
  return apiRequest<void>(`/api/leads/${leadId}`, {
    method: "DELETE"
  });
}
