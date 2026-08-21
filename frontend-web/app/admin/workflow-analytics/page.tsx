"use client";

import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/lib/api";
import Link from "next/link";

type WorkflowAnalytics = {
  workflow_id: string;
  workflow_name: string;
  total_runs: number;
  success_runs: number;
  failed_runs: number;
  success_rate: number;
  last_run: string | null;
};

export default function WorkflowAnalyticsPage() {
  const [items, setItems] = useState<WorkflowAnalytics[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("https://api.neuralshielddigital.com/api/admin/workflow-analytics", {
        cache: "no-store",
});
       const data = (await response.json()) as { items: WorkflowAnalytics[] };
        setItems(data.items || []);
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : "Failed to load workflow analytics.");
      }
    }

    load();
  }, []);

  const totals = useMemo(() => {
    const totalRuns = items.reduce((sum, item) => sum + item.total_runs, 0);
    const successRuns = items.reduce((sum, item) => sum + item.success_runs, 0);
    const failedRuns = items.reduce((sum, item) => sum + item.failed_runs, 0);
    const successRate = totalRuns > 0 ? Math.round((successRuns / totalRuns) * 100) : 0;

    return { totalRuns, successRuns, failedRuns, successRate };
  }, [items]);

  return (
    <main className="dashboard-shell p-8">
      <div className="mb-8 flex justify-between">
        <div>
          <p className="page-kicker">ADMIN</p>
          <h1 className="text-4xl font-bold">Workflow Analytics</h1>
          <p className="mt-2 text-sm text-steel">
            Monitor automation runs, success rate and failed workflows.
          </p>
        </div>
        <Link href="/admin" className="btn-secondary">Back</Link>
      </div>

      {error ? <p className="alert-error mb-4">{error}</p> : null}

      <div className="mb-8 grid gap-4 md:grid-cols-4">
        <Metric label="Total Runs" value={totals.totalRuns} />
        <Metric label="Successful Runs" value={totals.successRuns} />
        <Metric label="Failed Runs" value={totals.failedRuns} />
        <Metric label="Success Rate" value={`${totals.successRate}%`} />
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th>Name</th>
              <th>Total</th>
              <th>Success</th>
              <th>Failed</th>
              <th>Success Rate</th>
              <th>Last Run</th>
            </tr>
          </thead>
          <tbody>
            {items.length ? (
              items.map((w) => (
                <tr key={w.workflow_id}>
                  <td>{w.workflow_name}</td>
                  <td>{w.total_runs}</td>
                  <td>{w.success_runs}</td>
                  <td>{w.failed_runs}</td>
                  <td>{w.success_rate}%</td>
                  <td>{w.last_run ? new Date(w.last_run).toLocaleString() : "-"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6}>No workflow analytics found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric-card">
      <p className="text-xs font-semibold uppercase text-steel">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}
