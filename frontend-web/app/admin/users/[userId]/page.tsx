"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";
import { clearTokens, getAccessToken } from "@/lib/token-storage";

type CustomerDetail = {
  user: {
    user_id: string;
    email: string;
    role?: string;
    tenant_name?: string;
    is_active?: boolean;
    created_at?: string;
  };
  subscriptions?: any[];
  payments?: any[];
  affiliate?: any;
  audit_logs?: any[];
};

function formatDate(value?: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function UserDetailPage() {
  const router = useRouter();
  const params = useParams<{ userId: string }>();
  const [data, setData] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function updateUserStatus(isActive: boolean) {
    try {
      await apiRequest(`/api/admin/users/${params.userId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: isActive }),
      });
      window.location.reload();
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Could not update user status.");
    }
  }

  async function updateUserRole(role: string) {
    try {
      await apiRequest(`/api/admin/users/${params.userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      window.location.reload();
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Could not update user role.");
    }
  }


  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }

    apiRequest<CustomerDetail>(`/api/admin/customers/${params.userId}`)
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearTokens();
          router.replace("/login");
          return;
        }
        setError(err instanceof ApiError ? err.detail : "Could not load user.");
      })
      .finally(() => setLoading(false));
  }, [params.userId, router]);

  if (loading) return <main className="dashboard-shell p-8">Loading user...</main>;

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">User Detail</h1>
          </div>
          <Link href="/admin/users" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        {error ? <p className="alert-error">{error}</p> : null}

        {data ? (
          <div className="grid gap-6">
            <section className="surface-card p-6">
              <h2 className="text-xl font-semibold">Profile</h2>
              <div className="mt-4 grid gap-4 md:grid-cols-4">
                <div><p className="text-xs uppercase text-steel">Email</p><p>{data.user.email}</p></div>
                <div><p className="text-xs uppercase text-steel">Tenant</p><p>{data.user.tenant_name ?? "-"}</p></div>
                <div><p className="text-xs uppercase text-steel">Role</p><p>{data.user.role ?? "-"}</p></div>
                <div><p className="text-xs uppercase text-steel">Created</p><p>{formatDate(data.user.created_at)}</p></div>
                <div>
                  <p className="text-xs uppercase text-steel">Status</p>
                  <p>{data.user.is_active ? "Active" : "Disabled"}</p>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <select
                  className="rounded-xl border border-line bg-white px-4 py-2"
                  value={data.user.role ?? "USER"}
                  onChange={(e) => updateUserRole(e.target.value)}
                >
                  <option value="USER">USER</option>
                  <option value="ADMIN">ADMIN</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                </select>

                <button
                  className="btn-secondary px-4 py-2"
                  onClick={() => updateUserStatus(!data.user.is_active)}
                >
                  {data.user.is_active ? "Disable User" : "Enable User"}
                </button>
              </div>
            </section>

            <section className="surface-card overflow-hidden">
              <h2 className="p-6 text-xl font-semibold">Payments</h2>
              <table className="w-full text-left text-sm">
                <thead className="bg-linen/80 text-xs uppercase text-steel">
                  <tr><th className="p-4">Provider</th><th className="p-4">Amount</th><th className="p-4">Status</th><th className="p-4">Payment ID</th><th className="p-4">Created</th></tr>
                </thead>
                <tbody>
                  {(data.payments ?? []).length ? data.payments!.map((p, i) => (
                    <tr key={i} className="border-t border-line">
                      <td className="p-4">{p.provider ?? "-"}</td>
                      <td className="p-4">{p.currency ?? ""} {p.amount ?? "-"}</td>
                      <td className="p-4">{p.status ?? "-"}</td>
                      <td className="p-4">{p.provider_payment_id ?? "-"}</td>
                      <td className="p-4">{formatDate(p.created_at)}</td>
                    </tr>
                  )) : <tr><td className="p-4" colSpan={5}>No payments found.</td></tr>}
                </tbody>
              </table>
            </section>

            <section className="surface-card overflow-hidden">
              <h2 className="p-6 text-xl font-semibold">Subscriptions</h2>
              <table className="w-full text-left text-sm">
                <thead className="bg-linen/80 text-xs uppercase text-steel">
                  <tr><th className="p-4">Plan</th><th className="p-4">Status</th><th className="p-4">Start</th><th className="p-4">End</th><th className="p-4">Cancel</th></tr>
                </thead>
                <tbody>
                  {(data.subscriptions ?? []).length ? data.subscriptions!.map((s, i) => (
                    <tr key={i} className="border-t border-line">
                      <td className="p-4">{s.plan_name ?? "-"}</td>
                      <td className="p-4">{s.status ?? "-"}</td>
                      <td className="p-4">{formatDate(s.current_period_start)}</td>
                      <td className="p-4">{formatDate(s.current_period_end)}</td>
                      <td className="p-4">{s.cancel_at_period_end ? "Yes" : "No"}</td>
                    </tr>
                  )) : <tr><td className="p-4" colSpan={5}>No subscriptions found.</td></tr>}
                </tbody>
              </table>
            </section>

            <section className="surface-card overflow-hidden">
              <h2 className="p-6 text-xl font-semibold">Audit Logs</h2>
              <table className="w-full text-left text-sm">
                <thead className="bg-linen/80 text-xs uppercase text-steel">
                  <tr><th className="p-4">Action</th><th className="p-4">Metadata</th><th className="p-4">Created</th></tr>
                </thead>
                <tbody>
                  {(data.audit_logs ?? []).length ? data.audit_logs!.map((log, i) => (
                    <tr key={i} className="border-t border-line">
                      <td className="p-4">{log.action ?? "-"}</td>
                      <td className="p-4">{JSON.stringify(log.metadata ?? {})}</td>
                      <td className="p-4">{formatDate(log.created_at)}</td>
                    </tr>
                  )) : <tr><td className="p-4" colSpan={3}>No audit logs found.</td></tr>}
                </tbody>
              </table>
            </section>
          </div>
        ) : null}
      </div>
    </main>
  );
}
