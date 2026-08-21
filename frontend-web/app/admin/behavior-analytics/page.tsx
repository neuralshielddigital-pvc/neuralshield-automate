"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type BehaviorItem = {
  user_email: string;
  login_frequency: string;
  device_changes: number;
  location_anomaly: string;
  failed_logins: number;
  session_risk_score: number;
};

export default function BehaviorAnalyticsPage() {
  const [items, setItems] = useState<BehaviorItem[]>([]);

  useEffect(() => {
    apiRequest<{ items: BehaviorItem[] }>("/api/admin/behavior-analytics")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              User Behavior Analytics
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
                <th className="p-4">User</th>
                <th className="p-4">Login Frequency</th>
                <th className="p-4">Device Changes</th>
                <th className="p-4">Location Anomaly</th>
                <th className="p-4">Failed Logins</th>
                <th className="p-4">Risk Score</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? (
                items.map((u, i) => (
                  <tr key={i} className="border-b border-line">
                    <td className="p-4">{u.user_email}</td>
                    <td className="p-4">{u.login_frequency}</td>
                    <td className="p-4">{u.device_changes}</td>
                    <td className="p-4">{u.location_anomaly}</td>
                    <td className="p-4">{u.failed_logins}</td>
                    <td className="p-4">{u.session_risk_score}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="p-4" colSpan={6}>
                    No behavior analytics found.
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
