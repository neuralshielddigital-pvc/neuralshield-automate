"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type SecurityReport = {
  title: string;
  report_type: string;
  status: string;
  risk_level: string;
  summary: string;
  created_at: string;
};

export default function SecurityReportsPage() {
  const [items, setItems] = useState<SecurityReport[]>([]);

  useEffect(() => {
    apiRequest<{ items: SecurityReport[] }>("/api/admin/security-reports")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              AI Security Reports
            </h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">
            Back
          </Link>
        </div>

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-line/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">Title</th>
                <th className="p-4">Type</th>
                <th className="p-4">Status</th>
                <th className="p-4">Risk</th>
                <th className="p-4">Summary</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? (
                items.map((r, i) => (
                  <tr key={i} className="border-b border-line">
                    <td className="p-4">{r.title}</td>
                    <td className="p-4">{r.report_type}</td>
                    <td className="p-4">{r.status}</td>
                    <td className="p-4">{r.risk_level}</td>
                    <td className="p-4">{r.summary}</td>
                    <td className="p-4">
                      {new Date(r.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="p-4" colSpan={6}>
                    No reports found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
