
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";

type Workflow = {
  id: string;
  name?: string;
  trigger_type?: string;
  is_active?: boolean;
  created_at?: string;
};

type WorkflowRun = {
  id: string;
  workflow_id?: string;
  status?: string;
  logs?: any;
  created_at?: string;
};

function formatDate(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function exportCsv(items: Workflow[]) {
  const headers = ["Name", "Trigger", "Status", "Created"];

  const rows = items.map((w) => [
    w.name ?? "",
    w.trigger_type ?? "",
    w.is_active ? "Active" : "Inactive",
    w.created_at ?? "",
  ]);

  const csv = [headers, ...rows]
    .map((row) => row.join(","))
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = "workflows-report.csv";
  link.click();

  URL.revokeObjectURL(url);
}

export default function AdminWorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [error, setError] = useState("");
  const [runningId, setRunningId] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<{ items: Workflow[] }>("/api/workflows")
      .then((w) => {
        setError("");
        setWorkflows(w.items ?? []);
        setRuns([]);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load workflows.")
      );
  }, []);
  async function deleteWorkflow(id: string) {
  if (!confirm("Delete this workflow?")) return;

  try {
    await apiRequest(`/api/workflows/${id}`, {
      method: "DELETE",
    });

    setWorkflows((prev) => prev.filter((w) => w.id !== id));
  } catch (err) {
    console.error(err);
    alert("Failed to delete workflow");
  }
}
  async function runWorkflowNow(workflowId: string) {
    setError("");
    setRunningId(workflowId);
    try {
      const run = await apiRequest<WorkflowRun>(`/api/workflows/${workflowId}/run`, {
        method: "POST",
        body: JSON.stringify({
          source: "admin_manual_run",
          test: true,
          name: "Admin Test Lead",
          email: "admin-test@example.com",
          phone: "+10000000000",
          timestamp: new Date().toISOString(),
        }),
      });

      setError("");
      setRuns((current) => [run, ...current]);
      alert("Workflow executed successfully");
    } catch (err) {
      console.error(err);
      setError(err instanceof ApiError ? err.detail : "Failed to run workflow.");
    } finally {
      setRunningId(null);
    }
  }

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Workflow Control Center</h1>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => exportCsv(workflows)}
              className="btn-primary px-4 py-2"
            >
             <Link href="/workflows/new" className="btn-primary px-4 py-2"> Create Workflow</Link>
              Export CSV
            </button>

            <Link href="/admin" className="btn-secondary px-4 py-2">
              Back
            </Link>
          </div>
        </div>

        {error ? <p className="alert-error">{error}</p> : null}

        <section className="surface-card overflow-hidden">
          <h2 className="p-6 text-xl font-semibold">Workflows</h2>

          <table className="w-full text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">Name</th>
                <th className="p-4">Trigger</th>
                <th className="p-4">Status</th>
                <th className="p-4">Logs</th>
<th className="p-4">Created</th>
                <th className="p-4">Actions</th>
              </tr>
            </thead>

            <tbody>
              {workflows.length ? (
                workflows.map((w) => (
                  <tr key={w.id} className="border-t border-line">
                    <td className="p-4">{w.name ?? "-"}</td>
                    <td className="p-4">{w.trigger_type ?? "-"}</td>
                    <td className="p-4">{w.is_active ? "Active" : "Inactive"}</td>
                    <td className="p-4">{formatDate(w.created_at)}</td>
                    <td className="p-4">
                      <div className="flex gap-2">
  <a
    href={`/workflows/${w.id}`}
    className="btn-primary"
  >
    Edit
  </a>

  <button
    onClick={() => runWorkflowNow(w.id)}
    className="btn-secondary"
  >
    Run Now
  </button>

  <button
    onClick={() => deleteWorkflow(w.id)}
    className="btn-danger"
  >
    Delete
  </button>
</div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="p-4" colSpan={5}>No workflows found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <section className="surface-card mt-6 overflow-hidden">
          <h2 className="p-6 text-xl font-semibold">Workflow Runs</h2>

          <table className="w-full text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">Workflow ID</th>
                <th className="p-4">Status</th>
                <th className="p-4">Logs</th>
<th className="p-4">Created</th>
                <th className="p-4">Actions</th>
              </tr>
            </thead>

            <tbody>
              {runs.length ? (
                runs.map((r) => (
                  <tr key={r.id} className="border-t border-line">
                    <td className="p-4">{r.workflow_id ?? "-"}</td>
                    <td className="p-4">{r.status ?? "-"}</td>
<td className="p-4 text-xs whitespace-pre-wrap">{r.logs ? JSON.stringify(r.logs, null, 2) : "-"}</td>
<td className="p-4">{formatDate(r.created_at)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="p-4" colSpan={3}>No workflow runs found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
