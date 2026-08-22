"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Payment = {
  id: string;
  user_email?: string;
  amount: string;
  currency?: string;
  status: string;
  created_at: string;
};

export default function AdminPaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const res = await apiRequest<{ items: Payment[] }>("/api/admin/payments");
      setPayments(res.items || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <div>
          <p className="text-sm font-semibold text-ink">NeuralShieldDigital Admin</p>
          <p className="text-xs text-steel">Payments</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link href="/admin" className="btn-secondary px-3 py-2">Overview</Link>
          <Link href="/admin/customers" className="btn-secondary px-3 py-2">Customers</Link>
          <Link href="/admin/payments" className="btn-primary px-3 py-2">Payments</Link>
          <Link href="/admin/subscriptions" className="btn-secondary px-3 py-2">Subscriptions</Link>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="surface-card p-6">
          <h1 className="text-3xl font-semibold text-ink">Payments</h1>

          <div className="table-wrap mt-6">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="border-b border-line text-xs uppercase text-steel">
                <tr>
                  <th className="p-3">Customer</th>
                  <th className="p-3">Amount</th>
                  <th className="p-3">Currency</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Date</th>
                  <th className="p-3">Action</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} className="p-3">Loading...</td></tr>
                ) : payments.length === 0 ? (
                  <tr><td colSpan={6} className="p-3">No payments found.</td></tr>
                ) : (
                  payments.map((p) => {

                    return (
                      <tr key={p.id} className="border-b border-line">
                        <td className="p-3">{p.user_email || "-"}</td>
                        <td className="p-3">{p.amount}</td>
                        <td className="p-3">{p.currency || "-"}</td>
                        <td className="p-3">{p.status}</td>
                        <td className="p-3">{new Date(p.created_at).toLocaleDateString()}</td>
                        <td className="p-3">
                          <button
                            className="btn-secondary px-3 py-1"
                            disabled
                            title="Process refunds from the Paddle Transactions dashboard."
                            type="button"
                          >
                            Manage in Paddle
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  );
}
