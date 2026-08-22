"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";

type AuditLog = {
  id: string;
  user_email?: string;
  action?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
};

function formatDate(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function isSecurityEvent(log: AuditLog) {
  const action = String(log.action ?? "").toLowerCase();
  return (
    action.includes("login") ||
    action.includes("role") ||
    action.includes("password") ||
    action.includes("token") ||
    action.includes("payment") ||
    action.includes("subscription") ||
    action.includes("admin") ||
    action.includes("api")
  );
}

function exportCsv(items: AuditLog[]) {
  const headers = ["User", "Action", "Metadata", "Created"];
  const rows = items.map((l) => [
    l.user_email ?? "",
    l.action ?? "",
    JSON.stringify(l.metadata ?? {}),
    l.created_at ?? "",
  ]);

  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "security-events-report.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export default function SecurityEventsPage() {
  const [items, setItems] = useState<AuditLog[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<{ items: AuditLog[] }>("/api/admin/security-events")
      .then((res) => setItems(res.items ?? []))
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Could not load security events."));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Security Events</h1>
          </div>
          <div className="flex gap-3">
            <button onClick={() => exportCsv(items)} className="btn-primary px-4 py-2">Export CSV</button>
            <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
          </div>
        </div>

        {error ? <p className="alert-error">{error}</p> : null}

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">User</th>
                <th className="p-4">Action</th>
                <th className="p-4">Metadata</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? items.map((log) => (
                <tr key={log.id} className="border-t border-line">
                  <td className="p-4">{log.user_email ?? "-"}</td>
                  <td className="p-4 font-semibold">{log.action ?? "-"}</td>
                  <td className="p-4">{JSON.stringify(log.metadata ?? {})}</td>
                  <td className="p-4">{formatDate(log.created_at)}</td>
                </tr>
              )) : <tr><td className="p-4" colSpan={4}>No security events found.</td></tr>}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
