"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type RevenueData = {
  currency: string;
  total_revenue: number;
  monthly_revenue: number;
  active_subscriptions: number;
  total_customers: number;
};

export default function AdminRevenuePage() {
  const [data, setData] = useState<RevenueData | null>(null);

  useEffect(() => {
    apiRequest<RevenueData>("/api/admin/revenue").then(setData);
  }, []);

  return (
    <main className="dashboard-shell">
      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="text-3xl font-semibold text-ink">Revenue Reports</h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Card label="Total Revenue" value={`${data?.currency || "INR"} ${data?.total_revenue || 0}`} />
          <Card label="Monthly Revenue" value={`${data?.currency || "INR"} ${data?.monthly_revenue || 0}`} />
          <Card label="Active Subscriptions" value={String(data?.active_subscriptions || 0)} />
          <Card label="Total Customers" value={String(data?.total_customers || 0)} />
        </div>
      </section>
    </main>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-card p-6">
      <p className="text-xs uppercase text-steel">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}
