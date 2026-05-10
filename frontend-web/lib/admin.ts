import { apiRequest } from "@/lib/api";

export type AdminStats = {
  total_users: number;
  active_subscriptions: number;
  total_leads: number;
  workflows: number;
  affiliate_commissions: string;
};

export type AdminListResponse<T> = {
  items: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
};

export type AdminUser = {
  id: string;
  email: string;
  is_active: boolean;
  role: string;
  tenant_name: string | null;
  stripe_customer_id: string | null;
  created_at: string;
};

export type AdminSubscription = {
  id: string;
  user_email: string;
  tenant_name: string | null;
  plan_name: string;
  status: string;
  stripe_customer_id: string;
  current_period_end: string | null;
  created_at: string;
};

export type AdminLead = {
  id: string;
  tenant_name: string | null;
  name: string | null;
  email: string;
  phone: string | null;
  source: string | null;
  stage: string;
  tags: string[];
  created_at: string;
};

export type AdminWorkflow = {
  id: string;
  tenant_name: string | null;
  name: string;
  is_active: boolean;
  created_at: string;
};

export type AdminWorkflowRun = {
  id: string;
  workflow_name: string | null;
  tenant_name: string | null;
  status: string;
  logs: Record<string, unknown>;
  created_at: string;
};

export type AdminAffiliate = {
  id: string;
  user_email: string;
  referral_code: string;
  is_active: boolean;
  created_at: string;
};

export type AdminCommission = {
  id: string;
  referral_code: string | null;
  amount: string;
  status: string;
  created_at: string;
};

export type AdminAuditLog = {
  id: string;
  user_email: string | null;
  action: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export async function getAdminStats() {
  return apiRequest<AdminStats>("/api/admin/stats");
}

export async function getAdminUsers() {
  return apiRequest<AdminListResponse<AdminUser>>("/api/admin/users");
}

export async function getAdminSubscriptions() {
  return apiRequest<AdminListResponse<AdminSubscription>>("/api/admin/subscriptions");
}

export async function getAdminLeads() {
  return apiRequest<AdminListResponse<AdminLead>>("/api/admin/leads");
}

export async function getAdminWorkflows() {
  return apiRequest<AdminListResponse<AdminWorkflow>>("/api/admin/workflows");
}

export async function getAdminWorkflowRuns() {
  return apiRequest<AdminListResponse<AdminWorkflowRun>>("/api/admin/workflow-runs");
}

export async function getAdminAffiliates() {
  return apiRequest<AdminListResponse<AdminAffiliate>>("/api/admin/affiliates");
}

export async function getAdminCommissions() {
  return apiRequest<AdminListResponse<AdminCommission>>("/api/admin/commissions");
}

export async function getAdminAuditLogs() {
  return apiRequest<AdminListResponse<AdminAuditLog>>("/api/admin/audit-logs");
}
