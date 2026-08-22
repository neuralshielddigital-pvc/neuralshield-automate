"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";

type DeadLetterRun = {
  id: string;
  workflow_id?: string | null;
  workflow_name: string | null;
  tenant_id?: string | null;
  tenant_name?: string | null;
  status: string | null;
  retry_count: number;
  max_retries: number;
  last_error?: string | null;
  created_at: string;
};

export default function DeadLetterPage() {
  const [items, setItems] = useState<DeadLetterRun[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const query = new URLSearchParams();
        if (search) query.set("search", search);

        const qs = query.toString();
        const data = (await apiRequest(
          `/api/admin/workflow-runs?status=FAILED${qs ? `?${qs}` : ""}`
        )) as { items: DeadLetterRun[] };

        setItems(data.items || []);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [search]);

  return (
    <main className="dashboard-shell p-8">
      <div className="flex justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold">Failed Workflows</h1>
          <p className="text-sm opacity-70 mt-2">
            Failed workflow runs that may need retry or admin review.
          </p>
        </div>

        <Link href="/admin" className="btn-secondary">
          Back
        </Link>
      </div>

      <div className="flex gap-3 mb-4">
        <input
          className="border p-3 rounded"
          placeholder="Search workflow"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr>
              <th>Workflow</th>
              <th>Tenant</th>
              <th>Status</th>
              <th>Retry</th>
              <th>Last Error</th>
              <th>Created</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {items.map((run) => (
              <tr key={run.id}>
                <td>{run.workflow_name || "-"}</td>
                <td>{run.tenant_name || run.tenant_id || "-"}</td>
                <td>{run.status || "-"}</td>
                <td>
                  {run.retry_count}/{run.max_retries}
                </td>
                <td className="max-w-md">
                  <pre className="text-xs whitespace-pre-wrap">
                    {run.last_error || "-"}
                  </pre>
                </td>
                <td>{run.created_at}</td>
                <td>
                  <Link
                    href={`/admin/workflow-runs/${run.id}`}
                    className="btn-secondary"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}

            {!loading && items.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-4 text-center">
                  No failed workflow runs found.
                </td>
              </tr>
            ) : null}

            {loading ? (
              <tr>
                <td colSpan={7} className="p-4 text-center">
                  Loading Failed Workflows...
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </main>
  );
}
