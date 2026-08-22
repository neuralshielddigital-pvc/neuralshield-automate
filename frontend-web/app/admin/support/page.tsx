"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";

type SupportTicket = {
  id?: string;
  subject?: string;
  status?: string;
  priority?: string;
  assigned_to?: string;
  created_at?: string;
};

export default function SupportPage() {
  const [items, setItems] = useState<SupportTicket[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<{ items: SupportTicket[] }>("/api/admin/support")
      .then((res) => setItems(res.items ?? []))
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Could not load support tickets."));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Support Center</h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        {error ? <p className="alert-error">{error}</p> : null}

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">Subject</th>
                <th className="p-4">Status</th>
                <th className="p-4">Priority</th>
                <th className="p-4">Assigned</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? items.map((t, i) => (
                <tr key={t.id ?? i} className="border-t border-line">
                  <td className="p-4">{t.subject ?? "-"}</td>
                  <td className="p-4">{t.status ?? "-"}</td>
                  <td className="p-4">{t.priority ?? "-"}</td>
                  <td className="p-4">{t.assigned_to ?? "-"}</td>
                  <td className="p-4">{t.created_at ? new Date(t.created_at).toLocaleString() : "-"}</td>
                </tr>
              )) : <tr><td className="p-4" colSpan={5}>No support tickets found.</td></tr>}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
