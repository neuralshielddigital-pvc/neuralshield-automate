"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";

type WorkflowRun = {
  id: string;
  workflow_id?: string | null;
  workflow_name: string | null;
  tenant_id?: string | null;
  tenant_name?: string | null;
  status: string;
  logs: unknown;
  created_at: string;
};

export default function WorkflowRunsPage() {
  const [items, setItems] = useState<WorkflowRun[]>([]);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const query = new URLSearchParams();
        if (status) query.set("status", status);
        if (search) query.set("search", search);

        const qs = query.toString();
        const data = (await apiRequest(
          `/api/admin/workflow-runs${qs ? `?${qs}` : ""}`
        )) as { items: WorkflowRun[] };

        setItems(data.items || []);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [status, search]);

  return (
    <main className="dashboard-shell p-8">
      <div className="flex justify-between mb-8">
        <h1 className="text-4xl font-bold">Workflow Runs</h1>
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

        <select
          className="border p-3 rounded"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All Status</option>
          <option value="COMPLETED">Completed</option>
          <option value="FAILED">Failed</option>
          <option value="RUNNING">Running</option>
          <option value="QUEUED">Queued</option>
        </select>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr>
              <th>Workflow</th>
              <th>Tenant</th>
              <th>Status</th>
              <th>Logs</th>
              <th>Created</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((run) => (
              <tr key={run.id}>
                <td>{run.workflow_name || "-"}</td>
                <td>{run.tenant_name || run.tenant_id || "-"}</td>
                <td>{run.status}</td>
                <td>
                  <pre className="max-w-md overflow-x-auto text-xs whitespace-pre-wrap">
                    {JSON.stringify(run.logs, null, 2)}
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
                <td colSpan={6} className="p-4 text-center">
                  No workflow runs found.
                </td>
              </tr>
            ) : null}

            {loading ? (
              <tr>
                <td colSpan={6} className="p-4 text-center">
                  Loading workflow runs...
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </main>
  );
}
