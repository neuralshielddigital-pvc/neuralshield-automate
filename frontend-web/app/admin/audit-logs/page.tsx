"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";
import { clearTokens } from "@/lib/token-storage";

type AuditLog = {
  audit_log_id?: string;
  user_email?: string;
  tenant_name?: string;
  action: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
};

type AuditResponse = {
  items?: AuditLog[];
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
};

function formatDate(value?: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function AdminAuditLogsPage() {
  const router = useRouter();
  const [data, setData] = useState<AuditResponse | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  function loadLogs(query = "") {
    setLoading(true);
    setError("");

    const qs = new URLSearchParams();
    if (query.trim()) qs.set("search", query.trim());

    apiRequest<AuditResponse>(`/api/admin/audit-logs${qs.toString() ? `?${qs.toString()}` : ""}`)
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearTokens();
          router.replace("/login");
          return;
        }
        setError(err instanceof ApiError ? err.detail : "Could not load audit logs.");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Audit Logs</h1>
            <p className="text-steel">Security, login, admin, and platform activity history.</p>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <section className="surface-card mb-6 p-4">
          <form
            className="flex gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              loadLogs(search);
            }}
          >
            <input
              className="w-full rounded-2xl border border-line bg-white px-4 py-3"
              placeholder="Search action, user, tenant..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <button className="btn-primary px-5 py-3" type="submit">Search</button>
          </form>
        </section>

        {error ? <p className="alert-error mb-6">{error}</p> : null}
        {loading ? <p>Loading audit logs...</p> : null}

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">Action</th>
                <th className="p-4">User</th>
                <th className="p-4">Tenant</th>
                <th className="p-4">Metadata</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).length ? data!.items!.map((log, index) => (
                <tr key={log.audit_log_id ?? index} className="border-t border-line">
                  <td className="p-4 font-medium">{log.action}</td>
                  <td className="p-4">{log.user_email ?? "-"}</td>
                  <td className="p-4">{log.tenant_name ?? "-"}</td>
                  <td className="p-4 max-w-xl break-words">{JSON.stringify(log.metadata ?? {})}</td>
                  <td className="p-4">{formatDate(log.created_at)}</td>
                </tr>
              )) : (
                <tr>
                  <td className="p-4" colSpan={5}>No audit logs found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
