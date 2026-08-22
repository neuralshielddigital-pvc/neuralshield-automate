"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Threat = {
  user_email: string;
  threat_type: string;
  severity: string;
  status: string;
  details: string;
  created_at: string;
};

export default function InsiderThreatsPage() {
  const [items, setItems] = useState<Threat[]>([]);

  useEffect(() => {
    apiRequest<{ items: Threat[] }>("/api/admin/insider-threats")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Insider Threat Detection
            </h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">
            Back
          </Link>
        </div>

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">User</th>
                <th className="p-4">Threat</th>
                <th className="p-4">Severity</th>
                <th className="p-4">Status</th>
                <th className="p-4">Details</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((t, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="p-4">{t.user_email}</td>
                  <td className="p-4">{t.threat_type}</td>
                  <td className="p-4">{t.severity}</td>
                  <td className="p-4">{t.status}</td>
                  <td className="p-4">{t.details}</td>
                  <td className="p-4">
                    {new Date(t.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
