export type UserRole = "USER" | "ADMIN" | "SUPER_ADMIN";

export type AuthUser = {
  id: string;
  email: string;
  is_active: boolean;
  role: UserRole;
  tenant_id: string;
  created_at: string;
  updated_at: string;
};

export type AuthTenant = {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
  tenant: AuthTenant;
};

export type CurrentUserResponse = {
  user: AuthUser;
  tenant: AuthTenant;
};

export type PlanInterval = "monthly" | "yearly";
export type SubscriptionStatus = "ACTIVE" | "CANCELED" | "PAST_DUE" | "INCOMPLETE";

export type BillingPlan = {
  id: string;
  name: string;
  stripe_price_id: string;
  price: string;
  interval: PlanInterval;
};

export type Subscription = {
  id: string;
  stripe_customer_id: string;
  stripe_subscription_id: string;
  status: SubscriptionStatus;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  plan: BillingPlan;
};

export type SubscriptionResponse = {
  subscription: Subscription | null;
};

export type CommissionStatus = "PENDING" | "APPROVED" | "REJECTED" | "PAID";

export type Affiliate = {
  id: string;
  user_id: string;
  referral_code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AffiliateMeResponse = {
  is_registered: boolean;
  affiliate: Affiliate | null;
  referral_link: string | null;
};

export type AffiliateReferral = {
  id: string;
  affiliate_id: string;
  referred_user_id: string;
  referred_user_email: string;
  created_at: string;
};

export type AffiliateCommission = {
  id: string;
  affiliate_id: string;
  referral_id: string;
  amount: string;
  status: CommissionStatus;
  created_at: string;
  updated_at: string;
};

export type AffiliateStats = {
  total_referrals: number;
  pending_commissions: string;
  approved_commissions: string;
  paid_commissions: string;
};

export type CampaignType = "EMAIL" | "SMS" | "WHATSAPP";
export type CampaignStatus = "DRAFT" | "ACTIVE" | "PAUSED";

export type PaginationMeta = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type Campaign = {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  type: CampaignType;
  status: CampaignStatus;
  subject: string | null;
  message: string;
  created_at: string;
  updated_at: string;
};

export type CampaignListResponse = {
  items: Campaign[];
  pagination: PaginationMeta;
};

export type Lead = {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string | null;
  email: string;
  phone: string | null;
  source: string | null;
  stage: LeadStage;
  notes: string | null;
  last_contacted_at: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type LeadStage = "NEW" | "CONTACTED" | "QUALIFIED" | "WON" | "LOST";

export type LeadListResponse = {
  items: Lead[];
  pagination: PaginationMeta;
};

export type LeadImportResponse = {
  imported: number;
  updated: number;
  items: Lead[];
};

export type Workflow = {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  public_webhook_key: string;
  definition: Record<string, unknown>;
  triggers: WorkflowTrigger[];
  actions: WorkflowAction[];
  created_at: string;
  updated_at: string;
};

export type WorkflowTriggerType = "WEBHOOK_RECEIVED" | "NEW_LEAD" | "CAMPAIGN_ACTIVATED";
export type WorkflowActionType = "SEND_WEBHOOK" | "SEND_EMAIL" | "CREATE_LEAD" | "ADD_AUDIT_LOG";
export type WorkflowRunStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";

export type WorkflowTrigger = {
  id: string;
  workflow_id: string;
  type: WorkflowTriggerType;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type WorkflowAction = {
  id: string;
  workflow_id: string;
  type: WorkflowActionType;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type WorkflowRun = {
  id: string;
  workflow_id: string;
  status: WorkflowRunStatus;
  logs: Record<string, unknown>;
  trigger_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type WorkflowListResponse = {
  items: Workflow[];
  pagination: PaginationMeta;
};

export type WorkflowRunListResponse = {
  items: WorkflowRun[];
  pagination: PaginationMeta;
};

export type CampaignStats = {
  campaigns: number;
  active_campaigns: number;
  leads: number;
  workflows: number;
};
