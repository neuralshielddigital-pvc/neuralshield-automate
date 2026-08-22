"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiRequest } from "@/lib/api";

type CustomerDetail = Record<string, any>;

export default function AdminCustomerDetailPage() {
  const params = useParams<{ userId: string }>();
  const [data, setData] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await apiRequest<CustomerDetail>(`/api/admin/customers/${params.userId}`);
        setData(res);
      } finally {
        setLoading(false);
      }
    }
    if (params.userId) load();
  }, [params.userId]);

  const user = data?.user;
  const subscriptions = data?.subscriptions || [];
  const payments = data?.payments || [];
  const auditLogs = data?.audit_logs || [];
  const affiliate = data?.affiliate;

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <div>
          <p className="text-sm font-semibold text-ink">NeuralShieldDigital Admin</p>
          <p className="text-xs text-steel">Customer detail</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/admin" className="btn-secondary px-3 py-2">Overview</Link>
          <Link href="/admin/customers" className="btn-primary">Customers</Link>
          <Link href="/admin/payments" className="btn-secondary px-3 py-2">Payments</Link>
          <Link href="/admin/subscriptions" className="btn-secondary px-3 py-2">Subscriptions</Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-8">
        {loading ? <div className="surface-card p-6">Loading...</div> : null}

        {user ? (
          <>
            <div className="surface-card p-6">
              <p className="page-kicker">Customer</p>
              <h1 className="text-3xl font-semibold text-ink">{user.email}</h1>

              <div className="mt-6 grid gap-4 sm:grid-cols-4">
                <Info label="Role" value={user.role} />
                <Info label="Tenant" value={user.tenant_name} />
                <Info label="Active" value={user.is_active ? "Yes" : "No"} />
                <Info label="Created" value={date(user.created_at)} />
              </div>
            </div>

            <SimpleTable
              title="Subscriptions"
              columns={["Plan", "Status", "Start", "End", "Cancel at end"]}
              rows={subscriptions.map((s: any) => [
                s.plan_name,
                s.status,
                date(s.current_period_start),
                date(s.current_period_end),
                s.cancel_at_period_end ? "Yes" : "No",
              ])}
            />

            <SimpleTable
              title="Payments"
              columns={["Amount", "Currency", "Status", "Date"]}
              rows={payments.map((p: any) => [
                p.amount,
                p.currency,
                p.status,
                date(p.created_at),
              ])}
            />

            <SimpleTable
              title="Audit Logs"
              columns={["Action", "Created", "Metadata"]}
              rows={auditLogs.slice(0, 20).map((log: any) => [
                log.action,
                date(log.created_at),
                log.metadata ? JSON.stringify(log.metadata) : "-",
              ])}
            />
          </>
        ) : !loading ? (
          <div className="surface-card p-6">Customer not found.</div>
        ) : null}
      </section>
    </main>
  );
}

function Info({ label, value }: { label: string; value: any }) {
  return (
    <div className="metric-card">
      <p className="text-xs font-semibold uppercase text-steel">{label}</p>
      <p className="mt-2 text-lg font-semibold text-ink">{value || "-"}</p>
    </div>
  );
}

function SimpleTable({
  title,
  columns,
  rows,
}: {
  title: string;
  columns: string[];
  rows: any[][];
}) {
  return (
    <div className="surface-card p-6">
      <h2 className="text-xl font-semibold text-ink">{title}</h2>
      <div className="table-wrap mt-4">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-line text-xs uppercase text-steel">
            <tr>{columns.map((c) => <th key={c} className="p-3">{c}</th>)}</tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td className="p-3" colSpan={columns.length}>No records found.</td></tr>
            ) : (
              rows.map((row, i) => (
                <tr key={i} className="border-b border-line">
                  {row.map((cell, j) => <td key={j} className="p-3">{cell || "-"}</td>)}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function date(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "-" : d.toLocaleDateString();
}
