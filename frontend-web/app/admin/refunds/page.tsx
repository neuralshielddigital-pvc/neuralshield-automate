"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type RefundItem = {
  id: string;
  user_email?: string | null;
  provider?: string | null;
  plan_name?: string | null;
  amount: string;
  currency?: string | null;
  status: string;
  provider_payment_id?: string | null;
  provider_order_id?: string | null;
  created_at?: string;
};

export default function AdminRefundsPage() {
  const [items, setItems] = useState<RefundItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<{ items: RefundItem[] }>("/api/admin/refunds")
      .then((res) => setItems(res.items || []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="dashboard-shell">
      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="text-3xl font-semibold text-ink">Refunds</h1>
            <p className="mt-2 text-sm text-steel">Refunded, disputed, and failed payment records.</p>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <section className="surface-card overflow-hidden">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">Customer</th>
                <th className="p-4">Plan</th>
                <th className="p-4">Amount</th>
                <th className="p-4">Status</th>
                <th className="p-4">Provider</th>
                <th className="p-4">Payment ID</th>
                <th className="p-4">Date</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td className="p-4" colSpan={7}>Loading refunds...</td></tr>
              ) : items.length === 0 ? (
                <tr><td className="p-4" colSpan={7}>No refunds, disputes, or failed payments found.</td></tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="border-t border-line">
                    <td className="p-4">{item.user_email || "-"}</td>
                    <td className="p-4">{item.plan_name || "-"}</td>
                    <td className="p-4">{item.currency || "INR"} {item.amount}</td>
                    <td className="p-4 font-semibold">{item.status}</td>
                    <td className="p-4">{item.provider || "-"}</td>
                    <td className="p-4">{item.provider_payment_id || "-"}</td>
                    <td className="p-4">{item.created_at ? new Date(item.created_at).toLocaleDateString() : "-"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>
      </section>
    </main>
  );
}
