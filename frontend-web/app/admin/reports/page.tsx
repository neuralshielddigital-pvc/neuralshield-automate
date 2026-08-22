"use client";

import Link from "next/link";

export default function ReportsPage() {
  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Reports</h1>
            <p className="mt-2 text-sm text-steel">Export customer, billing, subscription, refund, and revenue reports.</p>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Link href="/admin/customers" className="surface-card p-6">
            <p className="text-xs font-semibold uppercase text-steel">CSV</p>
            <h2 className="mt-3 text-xl font-semibold text-ink">Customers Report</h2>
          </Link>

          <Link href="/admin/payments" className="surface-card p-6">
            <p className="text-xs font-semibold uppercase text-steel">CSV</p>
            <h2 className="mt-3 text-xl font-semibold text-ink">Payments Report</h2>
          </Link>

          <Link href="/admin/subscriptions" className="surface-card p-6">
            <p className="text-xs font-semibold uppercase text-steel">CSV</p>
            <h2 className="mt-3 text-xl font-semibold text-ink">Subscriptions Report</h2>
          </Link>

          <Link href="/admin/refunds" className="surface-card p-6">
            <p className="text-xs font-semibold uppercase text-steel">CSV</p>
            <h2 className="mt-3 text-xl font-semibold text-ink">Refunds Report</h2>
          </Link>

          <Link href="/admin/revenue" className="surface-card p-6">
            <p className="text-xs font-semibold uppercase text-steel">Dashboard</p>
            <h2 className="mt-3 text-xl font-semibold text-ink">Revenue Summary</h2>
          </Link>
        </div>
      </div>
    </main>
  );
}
