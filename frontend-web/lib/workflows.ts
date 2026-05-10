import { apiRequest, API_BASE_URL } from "@/lib/api";
import type {
  Workflow,
  WorkflowActionType,
  WorkflowListResponse,
  WorkflowRunListResponse,
  WorkflowTriggerType
} from "@/lib/types";

export type WorkflowActionPayload = {
  type: WorkflowActionType;
  config: Record<string, unknown>;
};

export type WorkflowPayload = {
  name: string;
  description?: string | null;
  is_active?: boolean;
  trigger: {
    type: WorkflowTriggerType;
    config: Record<string, unknown>;
  };
  actions: WorkflowActionPayload[];
};

export function workflowWebhookUrl(publicWebhookKey: string) {
  return `${API_BASE_URL}/api/webhooks/workflow/${publicWebhookKey}`;
}

export async function getWorkflows() {
  return apiRequest<WorkflowListResponse>("/api/workflows");
}

export async function getWorkflow(workflowId: string) {
  return apiRequest<Workflow>(`/api/workflows/${workflowId}`);
}

export async function createWorkflow(payload: WorkflowPayload) {
  return apiRequest<Workflow>("/api/workflows", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateWorkflow(workflowId: string, payload: Partial<WorkflowPayload>) {
  return apiRequest<Workflow>(`/api/workflows/${workflowId}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function deleteWorkflow(workflowId: string) {
  return apiRequest<void>(`/api/workflows/${workflowId}`, {
    method: "DELETE"
  });
}

export async function activateWorkflow(workflowId: string) {
  return apiRequest<Workflow>(`/api/workflows/${workflowId}/activate`, {
    method: "POST"
  });
}

export async function deactivateWorkflow(workflowId: string) {
  return apiRequest<Workflow>(`/api/workflows/${workflowId}/deactivate`, {
    method: "POST"
  });
}

export async function getWorkflowRuns(workflowId: string) {
  return apiRequest<WorkflowRunListResponse>(`/api/workflows/${workflowId}/runs`);
}
