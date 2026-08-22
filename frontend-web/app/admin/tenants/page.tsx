"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Tenant = {
  tenant_id: string;
  name: string;
  slug: string;
  total_users: number;
  active_users: number;
  active_subscriptions: number;
  total_revenue: string;
};

export default function AdminTenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);

  useEffect(() => {
    apiRequest<{ items: Tenant[] }>("/api/admin/tenants").then((res) =>
      setTenants(res.items || [])
    );
  }, []);

  return (
    <main className="dashboard-shell">
      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="text-3xl font-semibold text-ink">Tenant Management</h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <div className="surface-card p-6">
          <div className="table-wrap mt-4">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr>
                  <th className="p-3">Name</th>
                  <th className="p-3">Slug</th>
                  <th className="p-3">Users</th>
                  <th className="p-3">Active Users</th>
                  <th className="p-3">Subscriptions</th>
                  <th className="p-3">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((t) => (
                  <tr key={t.tenant_id}>
                    <td className="p-3">{t.name}</td>
                    <td className="p-3">{t.slug}</td>
                    <td className="p-3">{t.total_users}</td>
                    <td className="p-3">{t.active_users}</td>
                    <td className="p-3">{t.active_subscriptions}</td>
                    <td className="p-3">INR {t.total_revenue}</td>
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
