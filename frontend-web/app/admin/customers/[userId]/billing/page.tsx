"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiRequest } from "@/lib/api";

export default function BillingPage() {
  const { userId } = useParams();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    async function load() {
      const res = await apiRequest(`/api/admin/customers/${userId}`);
      setData(res);
    }
    load();
  }, [userId]);

  if (!data) return <div className="p-8">Loading...</div>;

  const totalSpent =
    data.payments?.reduce((sum: number, p: any) => sum + Number(p.amount || 0), 0) || 0;

  return (
    <main className="dashboard-shell">
      <section className="mx-auto max-w-7xl px-4 py-8 space-y-8">

        <div className="surface-card p-6">
          <h1 className="text-3xl font-semibold">{data.user.email}</h1>

          <div className="grid grid-cols-4 gap-4 mt-6">
            <div className="surface-card p-4">
              <p>Total Payments</p>
              <h2>{data.payments?.length || 0}</h2>
            </div>

            <div className="surface-card p-4">
              <p>Total Subscriptions</p>
              <h2>{data.subscriptions?.length || 0}</h2>
            </div>

            <div className="surface-card p-4">
              <p>Total Spent</p>
              <h2>₹{totalSpent}</h2>
            </div>

            <div className="surface-card p-4">
              <p>Status</p>
              <h2>{data.user.is_active ? "Active" : "Suspended"}</h2>
            </div>
          </div>
        </div>

        <div className="surface-card p-6">
          <h2 className="text-xl mb-4">Payments</h2>
          <table className="w-full">
            <thead>
              <tr>
                <th>Amount</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {data.payments?.map((p: any) => (
                <tr key={p.id}>
                  <td>{p.amount}</td>
                  <td>{p.status}</td>
                  <td>{new Date(p.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </section>
    </main>
  );
}
