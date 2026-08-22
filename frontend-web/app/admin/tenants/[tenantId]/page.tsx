"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";
import { clearTokens } from "@/lib/token-storage";

type TenantDetail = {
  tenant: { tenant_id: string; name: string; slug: string; created_at?: string };
  summary: {
    total_users: number;
    active_users: number;
    active_subscriptions: number;
    total_revenue: string;
  };
  users: any[];
  subscriptions: any[];
  payments: any[];
  audit_logs: any[];
};

function money(value: string | number | null | undefined) {
  return `INR ${Number(value ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function formatDate(value?: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function TenantDetailPage() {
  const router = useRouter();
  const params = useParams<{ tenantId: string }>();
  const [data, setData] = useState<TenantDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<TenantDetail>(`/api/admin/tenants/${params.tenantId}`)
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearTokens();
          router.replace("/login");
          return;
        }
        setError(err instanceof ApiError ? err.detail : "Could not load tenant.");
      })
      .finally(() => setLoading(false));
  }, [params.tenantId, router]);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">Admin</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Tenant Detail</h1>
          </div>
          <Link href="/admin/tenants" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        {loading ? <p>Loading tenant...</p> : null}
        {error ? <p className="alert-error mb-6">{error}</p> : null}

        {data ? (
          <div className="grid gap-6">
            <section className="surface-card p-6">
              <h2 className="text-xl font-semibold">Tenant Profile</h2>
              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <div><p className="text-xs uppercase text-steel">Name</p><p>{data.tenant.name}</p></div>
                <div><p className="text-xs uppercase text-steel">Slug</p><p>{data.tenant.slug}</p></div>
                <div><p className="text-xs uppercase text-steel">Created</p><p>{formatDate(data.tenant.created_at)}</p></div>
              </div>
            </section>

            <section className="grid gap-4 md:grid-cols-4">
              <div className="surface-card p-5"><p className="text-xs uppercase text-steel">Total Users</p><p className="mt-2 text-2xl font-semibold">{data.summary.total_users}</p></div>
              <div className="surface-card p-5"><p className="text-xs uppercase text-steel">Active Users</p><p className="mt-2 text-2xl font-semibold">{data.summary.active_users}</p></div>
              <div className="surface-card p-5"><p className="text-xs uppercase text-steel">Active Subs</p><p className="mt-2 text-2xl font-semibold">{data.summary.active_subscriptions}</p></div>
              <div className="surface-card p-5"><p className="text-xs uppercase text-steel">Revenue</p><p className="mt-2 text-2xl font-semibold">{money(data.summary.total_revenue)}</p></div>
            </section>

            <Table title="Users" columns={["Email", "Role", "Status", "Created"]} rows={data.users.map((u) => [u.email, u.role, u.is_active ? "Active" : "Inactive", formatDate(u.created_at)])} />
            <Table title="Subscriptions" columns={["Plan", "Status", "Period End", "Created"]} rows={data.subscriptions.map((s) => [s.plan_name ?? "-", s.status, formatDate(s.current_period_end), formatDate(s.created_at)])} />
            <Table title="Payments" columns={["Provider", "Amount", "Status", "Created"]} rows={data.payments.map((p) => [p.provider, `${p.currency} ${p.amount}`, p.status, formatDate(p.created_at)])} />
            <Table title="Audit Logs" columns={["Action", "Metadata", "Created"]} rows={data.audit_logs.map((l) => [l.action, JSON.stringify(l.metadata ?? {}), formatDate(l.created_at)])} />
          </div>
        ) : null}
      </div>
    </main>
  );
}

function Table({ title, columns, rows }: { title: string; columns: string[]; rows: any[][] }) {
  return (
    <section className="surface-card overflow-hidden">
      <h2 className="p-6 text-xl font-semibold">{title}</h2>
      <table className="w-full text-left text-sm">
        <thead className="bg-linen/80 text-xs uppercase text-steel">
          <tr>{columns.map((c) => <th key={c} className="p-4">{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length ? rows.map((row, i) => (
            <tr key={i} className="border-t border-line">
              {row.map((cell, j) => <td key={j} className="p-4">{cell}</td>)}
            </tr>
          )) : (
            <tr><td className="p-4" colSpan={columns.length}>No data found.</td></tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
