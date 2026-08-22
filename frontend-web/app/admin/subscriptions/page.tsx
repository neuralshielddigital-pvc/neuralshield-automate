"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Subscription = {
  id: string;
  user_email?: string;
  tenant_name?: string;
  plan_name?: string;
  status: string;
  current_period_end?: string;
};

export default function AdminSubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const res = await apiRequest<{ items: Subscription[] }>("/api/admin/subscriptions");
      setSubscriptions(res.items || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function action(id: string, path: string, status: string) {
    await apiRequest(`/api/admin/subscriptions/${id}/${path}`, { method: "PATCH" });
    setSubscriptions((items) =>
      items.map((item) => (item.id === id ? { ...item, status } : item))
    );
  }

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <div>
          <p className="text-sm font-semibold text-ink">NeuralShieldDigital Admin</p>
          <p className="text-xs text-steel">Subscriptions</p>
        </div>
        <Link href="/admin" className="btn-secondary px-3 py-2">Back</Link>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="surface-card p-6">
          <h1 className="text-3xl font-semibold text-ink">Subscriptions</h1>

          <div className="table-wrap mt-6">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="border-b border-line text-xs uppercase text-steel">
                <tr>
                  <th className="p-3">User</th>
                  <th className="p-3">Plan</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Tenant</th>
                  <th className="p-3">Ends</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr><td colSpan={6} className="p-3">Loading...</td></tr>
                ) : subscriptions.length === 0 ? (
                  <tr><td colSpan={6} className="p-3">No subscriptions found.</td></tr>
                ) : (
                  subscriptions.map((s) => (
                    <tr key={s.id} className="border-b border-line">
                      <td className="p-3">{s.user_email || "-"}</td>
                      <td className="p-3">{s.plan_name || "-"}</td>
                      <td className="p-3">{s.status}</td>
                      <td className="p-3">{s.tenant_name || "-"}</td>
                      <td className="p-3">
                        {s.current_period_end
                          ? new Date(s.current_period_end).toLocaleDateString()
                          : "-"}
                      </td>
                      <td className="p-3 flex gap-2">
                        {s.status === "ACTIVE" && (
                          <>
                            <button className="btn-secondary px-3 py-1" onClick={() => action(s.id, "pause", "PAUSED")}>Pause</button>
                            <button className="btn-secondary px-3 py-1 text-red-600" onClick={() => action(s.id, "cancel", "CANCELED")}>Cancel</button>
                          </>
                        )}

                        {s.status === "PAUSED" && (
                          <button className="btn-primary px-3 py-1" onClick={() => action(s.id, "reactivate", "ACTIVE")}>Reactivate</button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  );
}
