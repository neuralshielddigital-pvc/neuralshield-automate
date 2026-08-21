import { apiRequest, API_BASE_URL } from "@/lib/api";

import type {
  Workflow,
  WorkflowActionType,
  WorkflowListResponse,
  WorkflowRun,
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
  schedule_enabled?: boolean;
  schedule_cron?: string | null;
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
import { getAccessToken } from "@/lib/auth";

export async function cloneWorkflowTemplate(templateId: string): Promise<{
  id: string;
  name: string;
  already_installed?: boolean;
}> {
  const token = getAccessToken();

  return apiRequest(`/api/workflow-templates/${templateId}/clone`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
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

export async function getWorkflowTemplates() {
  return apiRequest<{
    items: {
      id: string;
      name: string;
      description?: string;
      trigger_type: string;
      action_type: string;
      config?: Record<string, unknown>;
    }[];
  }>("/api/workflow-templates");
}

export async function runWorkflowNow(workflowId: string) {
  return apiRequest<WorkflowRun>(`/api/workflows/${workflowId}/run`, {
    method: "POST",
    body: JSON.stringify({
      source: "dashboard_test",
      test: true,
      name: "Dashboard Test Lead",
      email: "dashboard-test@example.com",
      phone: "+10000000000",
      timestamp: new Date().toISOString(),
    }),
  });
}
