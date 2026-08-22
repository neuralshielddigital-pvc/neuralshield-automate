"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AdminAffiliate,
  AdminAuditLog,
  AdminCommission,
  AdminLead,
  AdminStats,
  AdminSubscription,
  AdminUser,
  AdminWorkflow,
  AdminWorkflowRun,
  getAdminAffiliates,
  getAdminAuditLogs,
  getAdminCommissions,
  getAdminLeads,
  getAdminStats,
  getAdminSubscriptions,
  getAdminUsers,
  getAdminWorkflows,
  getAdminWorkflowRuns
} from "@/lib/admin";
import { ApiError } from "@/lib/api";
import { getMe } from "@/lib/auth";
import { clearTokens, getAccessToken } from "@/lib/token-storage";

export default function AdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [subscriptions, setSubscriptions] = useState<AdminSubscription[]>([]);
  const [leads, setLeads] = useState<AdminLead[]>([]);
  const [workflows, setWorkflows] = useState<AdminWorkflow[]>([]);
  const [workflowRuns, setWorkflowRuns] = useState<AdminWorkflowRun[]>([]);
  const [affiliates, setAffiliates] = useState<AdminAffiliate[]>([]);
  const [commissions, setCommissions] = useState<AdminCommission[]>([]);
  const [auditLogs, setAuditLogs] = useState<AdminAuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const token = getAccessToken();
    if (!token) {
      setRedirecting(true);
      setLoading(false);
      router.replace("/login");
      return () => {
        active = false;
      };
    }

    async function loadAdmin() {
      try {
        const session = await getMe();
        if (session.user.role !== "ADMIN" && session.user.role !== "SUPER_ADMIN") {
          if (active) {
            setRedirecting(true);
          }
          router.replace("/dashboard");
          return;
        }
        const [
          statsResponse,
          usersResponse,
          subscriptionsResponse,
          leadsResponse,
          workflowsResponse,
          workflowRunsResponse,
          affiliatesResponse,
          commissionsResponse,
          auditLogsResponse
        ] = await Promise.all([
          getAdminStats(),
          getAdminUsers(),
          getAdminSubscriptions(),
          getAdminLeads(),
          getAdminWorkflows(),
          getAdminWorkflowRuns(),
          getAdminAffiliates(),
          getAdminCommissions(),
          getAdminAuditLogs()
        ]);
        if (!active) {
          return;
        }
        setStats(statsResponse);
        setUsers(usersResponse.items);
        setSubscriptions(subscriptionsResponse.items);
        setLeads(leadsResponse.items);
        setWorkflows(workflowsResponse.items);
        setWorkflowRuns(workflowRunsResponse.items);
        setAffiliates(affiliatesResponse.items);
        setCommissions(commissionsResponse.items);
        setAuditLogs(auditLogsResponse.items);
      } catch (err) {
        if (!active) {
          return;
        }
        if (err instanceof ApiError && err.status === 401) {
          clearTokens();
          setRedirecting(true);
          router.replace("/login");
          return;
        }
        setError(err instanceof ApiError ? err.detail : "Could not load admin dashboard.");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadAdmin();
    return () => {
      active = false;
    };
  }, [router]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4 text-sm font-medium text-steel">
        <div className="surface-card flex items-center gap-3 px-5 py-4">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-pine" />
          Loading admin...
        </div>
      </main>
    );
  }

  if (redirecting) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4 text-sm font-medium text-steel">
        <div className="surface-card flex items-center gap-3 px-5 py-4">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-pine" />
          Redirecting...
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4">
          <div className="flex shrink-0 items-center gap-3">
            <div className="brand-mark h-11 w-11 ring-4 ring-mint/70">
              NS
            </div>
            <div>
              <p className="text-sm font-semibold text-ink">NeuralShieldDigital Admin</p>
              <p className="text-xs text-steel">Platform control center</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Link href="/admin/customers" className="btn-primary">Customers</Link>
            <Link href="/admin/payments" className="btn-secondary px-3 py-2">Payments</Link>
            <Link href="/admin/revenue" className="btn-secondary px-3 py-2">Revenue</Link>
            <Link href="/admin/refunds" className="btn-secondary px-3 py-2">Refunds</Link>
            <Link href="/admin/subscriptions" className="btn-secondary px-3 py-2">Subscriptions</Link>
          <Link href="/admin/workflow-runs" className="btn-secondary px-3 py-2">Workflow Runs</Link>
          <Link href="/admin/dead-letter" className="btn-secondary px-3 py-2">Dead Letter Queue</Link>
          <Link href="/admin/queue-dashboard" className="btn-secondary px-3 py-2">Queue Dashboard</Link>
          <Link href="/admin/workflow-templates" className="btn-secondary px-3 py-2">Workflow Templates</Link>
          <Link href="/admin/workflow-analytics" className="btn-secondary px-3 py-2">Workflow Analytics</Link>
            <Link href="/admin/tenants" className="btn-secondary px-3 py-2">Tenants</Link>
            <Link href="/admin/analytics" className="btn-secondary px-3 py-2">Analytics</Link>
            <Link href="/admin/backups" className="btn-secondary px-3 py-2">Backups</Link>
<Link href="/admin/workflows" className="btn-secondary px-3 py-2">Workflows</Link>
            <Link href="/admin/affiliates" className="btn-secondary px-3 py-2">Affiliates</Link>
            <Link href="/admin/reports" className="btn-secondary px-3 py-2">Reports</Link>
            <Link href="/admin/api-keys" className="btn-secondary px-3 py-2">API Keys</Link>
            <Link href="/admin/security-events" className="btn-secondary px-3 py-2">Security Events</Link>
            <Link href="/admin/incidents" className="btn-secondary px-3 py-2">Incidents</Link>
            <Link href="/admin/support" className="btn-secondary px-3 py-2">Support</Link>
            <Link href="/admin/settings" className="btn-secondary px-3 py-2">Settings</Link>
            <Link href="/admin/system-health" className="btn-secondary px-3 py-2">System Health</Link>
            <Link href="/admin/audit-logs" className="btn-secondary px-3 py-2">Audit Logs</Link>
            <Link href="/admin/users" className="btn-secondary px-3 py-2">Users</Link>
            <Link href="/dashboard" className="btn-secondary px-3 py-2">Dashboard</Link>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:py-8">
        <section className="surface-card p-6 sm:p-8">
          <p className="page-kicker">Operations</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Admin dashboard</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
            Monitor platform activity, subscriptions, workflows, affiliates, and audit events from one secure view.
          </p>
          {error ? <p className="alert-error mt-4">{error}</p> : null}
          <div className="mt-6 grid gap-4 md:grid-cols-5">
            {[
              ["Total users", stats?.total_users ?? 0],
              ["Active subscriptions", stats?.active_subscriptions ?? 0],
              ["Total leads", stats?.total_leads ?? 0],
              ["Workflows", stats?.workflows ?? 0],
              ["Commissions", stats?.affiliate_commissions ?? "0"]
            ].map(([label, value]) => (
              <div className="metric-card" key={label}>
                <p className="text-xs font-semibold uppercase text-steel">{label}</p>
                <p className="mt-2 text-xl font-semibold text-ink">{value}</p>
              </div>
            ))}
          </div>
        </section>

        <AdminTable
          columns={["Email", "Role", "Tenant", "Active", "Created"]}
          rows={users.map((user) => [user.email, user.role, user.tenant_name ?? "-", user.is_active ? "Yes" : "No", formatDate(user.created_at)])}
          title="Users"
        />
        <AdminTable
          columns={["User", "Plan", "Status", "Tenant", "Period end"]}
          rows={subscriptions.map((item) => [item.user_email, item.plan_name, item.status, item.tenant_name ?? "-", formatDate(item.current_period_end)])}
          title="Subscriptions"
        />
        <AdminTable
          columns={["Name", "Email", "Source", "Stage", "Tenant"]}
          rows={leads.map((lead) => [lead.name ?? "-", lead.email, lead.source ?? "-", lead.stage, lead.tenant_name ?? "-"])}
          title="Leads"
        />
        <AdminTable
          columns={["Name", "Tenant", "Active", "Created"]}
          rows={workflows.map((workflow) => [workflow.name, workflow.tenant_name ?? "-", workflow.is_active ? "Yes" : "No", formatDate(workflow.created_at)])}
          title="Workflows"
        />
        <AdminTable
          columns={["Workflow", "Tenant", "Status", "Created"]}
          rows={workflowRuns.map((run) => [run.workflow_name ?? "-", run.tenant_name ?? "-", run.status, formatDate(run.created_at)])}
          title="Workflow runs"
        />
        <AdminTable
          columns={["User", "Referral code", "Active", "Created"]}
          rows={affiliates.map((affiliate) => [affiliate.user_email, affiliate.referral_code, affiliate.is_active ? "Yes" : "No", formatDate(affiliate.created_at)])}
          title="Affiliates"
        />
        <AdminTable
          columns={["Referral code", "Amount", "Status", "Created"]}
          rows={commissions.map((commission) => [commission.referral_code ?? "-", commission.amount, commission.status, formatDate(commission.created_at)])}
          title="Commissions"
        />
        <AdminTable
          columns={["User", "Action", "Metadata", "Created"]}
          rows={auditLogs.map((log) => [log.user_email ?? "-", log.action, JSON.stringify(log.metadata), formatDate(log.created_at)])}
          title="Audit logs"
        />
      </div>
    </main>
  );
}

function AdminTable({ title, columns, rows }: { title: string; columns: string[]; rows: Array<Array<string | number>> }) {
  return (
    <section className="admin-table p-6">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <div className="table-wrap">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-line text-xs uppercase text-steel">
            <tr>
              {columns.map((column) => (
                <th className="py-3 pr-4" key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr className="border-b border-line/70" key={`${title}-${index}`}>
                {row.map((cell, cellIndex) => (
                  <td className="max-w-[360px] truncate py-3 pr-4 text-steel" key={`${title}-${index}-${cellIndex}`}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr><td className="py-5 text-steel" colSpan={columns.length}>No records found.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}
