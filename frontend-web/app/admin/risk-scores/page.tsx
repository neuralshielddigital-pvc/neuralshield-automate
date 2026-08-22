"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type RiskItem = {
  user_email: string;
  risk_score: number;
  risk_level: string;
  last_activity: string;
  created_at: string;
};

export default function RiskScoresPage() {
  const [items, setItems] = useState<RiskItem[]>([]);

  useEffect(() => {
    apiRequest<{ items: RiskItem[] }>("/api/admin/risk-scores")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Risk Monitoring
            </h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">
            Back
          </Link>
        </div>

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="p-4">User</th>
                <th className="p-4">Risk Score</th>
                <th className="p-4">Risk Level</th>
                <th className="p-4">Activity</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r, i) => (
                <tr key={i}>
                  <td className="p-4">{r.user_email}</td>
                  <td className="p-4">{r.risk_score}</td>
                  <td className="p-4">{r.risk_level}</td>
                  <td className="p-4">{r.last_activity}</td>
                  <td className="p-4">
                    {new Date(r.created_at).toLocaleString()}
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
