"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type ActivityItem = {
  user_email: string;
  action: string;
  resource: string;
  severity: string;
  created_at: string;
};

export default function ActivityMonitorPage() {
  const [items, setItems] = useState<ActivityItem[]>([]);

  useEffect(() => {
    apiRequest<{ items: ActivityItem[] }>("/api/admin/activity-monitor")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Activity Monitoring
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
                <th className="p-4">Action</th>
                <th className="p-4">Resource</th>
                <th className="p-4">Severity</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a, i) => (
                <tr key={i}>
                  <td className="p-4">{a.user_email}</td>
                  <td className="p-4">{a.action}</td>
                  <td className="p-4">{a.resource}</td>
                  <td className="p-4">{a.severity}</td>
                  <td className="p-4">
                    {new Date(a.created_at).toLocaleString()}
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
