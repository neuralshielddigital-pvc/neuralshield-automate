"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type AccessItem = {
  user_email: string;
  role: string;
  permission_change: string;
  risk_level: string;
  status: string;
  created_at: string;
};

export default function AccessControlPage() {
  const [items, setItems] = useState<AccessItem[]>([]);

  useEffect(() => {
    apiRequest<{ items: AccessItem[] }>("/api/admin/access-control")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Access Control Monitoring
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
                <th className="p-4">Role</th>
                <th className="p-4">Permission Change</th>
                <th className="p-4">Risk</th>
                <th className="p-4">Status</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="p-4">{item.user_email}</td>
                  <td className="p-4">{item.role}</td>
                  <td className="p-4">{item.permission_change}</td>
                  <td className="p-4">{item.risk_level}</td>
                  <td className="p-4">{item.status}</td>
                  <td className="p-4">
                    {new Date(item.created_at).toLocaleString()}
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
