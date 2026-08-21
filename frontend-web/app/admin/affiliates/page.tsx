"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Affiliate = {
  id: string;
  user_id: string;
  user_email: string;
  referral_code: string;
  is_active: boolean;
  created_at: string;
};

export default function AdminAffiliatesPage() {
  const [items, setItems] = useState<Affiliate[]>([]);

  useEffect(() => {
    apiRequest<{ items: Affiliate[] }>("/api/admin/affiliates").then((res) =>
      setItems(res.items || [])
    );
  }, []);

  return (
    <main className="dashboard-shell">
      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="text-3xl font-semibold text-ink">Affiliate Management</h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <div className="surface-card p-6">
          <div className="table-wrap mt-4">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr>
                  <th className="p-3">Email</th>
                  <th className="p-3">Referral Code</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((a) => (
                  <tr key={a.id}>
                    <td className="p-3">{a.user_email}</td>
                    <td className="p-3">{a.referral_code}</td>
                    <td className="p-3">
                      {a.is_active ? "ACTIVE" : "INACTIVE"}
                    </td>
                    <td className="p-3">
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  );
}
