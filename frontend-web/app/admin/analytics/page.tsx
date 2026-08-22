"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

export default function AdminAnalyticsPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    apiRequest<any>("/api/admin/analytics").then(setData);
  }, []);

  const k = data?.kpis || {};

  return (
    <main className="dashboard-shell">
      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="text-3xl font-semibold text-ink">Analytics</h1>
            <p className="mt-2 text-sm text-steel">Revenue, customers, subscriptions and affiliate performance.</p>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Total Customers" value={k.total_customers ?? 0} />
          <Metric label="Active Subscriptions" value={k.active_subscriptions ?? 0} />
          <Metric label="Cancelled Subscriptions" value={k.cancelled_subscriptions ?? 0} />
          <Metric label="Monthly Revenue" value={`INR ${k.monthly_revenue ?? 0}`} />
          <Metric label="Lifetime Revenue" value={`INR ${k.lifetime_revenue ?? 0}`} />
          <Metric label="Total Affiliates" value={k.total_affiliates ?? 0} />
          <Metric label="Pending Commissions" value={`INR ${k.pending_commissions ?? 0}`} />
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <Table
            title="Revenue Last 30 Days"
            columns={["Date", "Revenue"]}
            rows={(data?.revenue_last_30_days || []).map((r: any) => [r.date, `INR ${r.revenue}`])}
          />

          <Table
            title="Revenue Last 12 Months"
            columns={["Month", "Revenue"]}
            rows={(data?.revenue_last_12_months || []).map((r: any) => [r.month, `INR ${r.revenue}`])}
          />

          <Table
            title="Subscription Status"
            columns={["Status", "Count"]}
            rows={(data?.subscription_status || []).map((r: any) => [r.status, r.count])}
          />
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: any }) {
  return (
    <div className="metric-card">
      <p className="text-xs font-semibold uppercase text-steel">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}

function Table({ title, columns, rows }: { title: string; columns: string[]; rows: any[][] }) {
  return (
    <div className="surface-card p-6">
      <h2 className="text-xl font-semibold text-ink">{title}</h2>
      <div className="table-wrap mt-4">
        <table className="w-full text-sm">
          <thead>
            <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={columns.length}>No data.</td></tr>
            ) : rows.map((row, i) => (
              <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
