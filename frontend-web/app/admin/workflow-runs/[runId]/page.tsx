"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";

type AnyObj = Record<string, any>;

export default function WorkflowRunDetailPage() {
  const params = useParams();
  const runId = String(params?.runId || "");

  const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.neuralshielddigital.com";

  const [run, setRun] = useState<AnyObj | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);
  const [retryMsg, setRetryMsg] = useState("");

  const authHeaders = (): Record<string, string> => {
    if (typeof window === "undefined") return {};

    const token =
      localStorage.getItem("access_token") ||
      localStorage.getItem("accessToken") ||
      localStorage.getItem("token") ||
      localStorage.getItem("authToken") ||
      localStorage.getItem("admin_token") ||
      localStorage.getItem("adminToken") ||
      localStorage.getItem("jwt") ||
      localStorage.getItem("neuralshield_token") ||
      "";

    if (!token) return {};

    return { Authorization: `Bearer ${token}` };
  };

  const fetchRun = async () => {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/admin/workflow-runs`, {
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        credentials: "include",
      });

      if (!res.ok) {
        throw new Error(`Failed to load workflow runs: ${res.status}`);
      }

      const data = await res.json();
      const list = Array.isArray(data)
        ? data
        : data.items || data.runs || data.data || [];

      const found = list.find((item: AnyObj) => {
        const id = item.id || item.run_id || item.workflow_run_id;
        return String(id) === runId;
      });

      if (!found) {
        setRun(null);
        setError("Workflow run not found.");
        return;
      }

      setRun(found);
    } catch (err: any) {
      setError(err?.message || "Failed to load workflow run.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (runId) fetchRun();
  }, [runId]);

  const status = String(run?.status || run?.state || "unknown").toUpperCase();

  const workflowName =
    run?.workflow_name ||
    run?.workflow?.name ||
    run?.name ||
    `Workflow Run ${runId}`;

  const workflowId =
    run?.workflow_id || run?.workflowId || run?.workflow?.id || "";

  const triggerPayload =
    run?.trigger_payload ||
    run?.payload ||
    run?.input ||
    run?.triggerPayload ||
    {};

  const executionLogs =
    run?.execution_logs ||
    run?.logs ||
    run?.steps ||
    run?.output ||
    [];

  const errorMessage =
    run?.error_message ||
    run?.error ||
    run?.failure_reason ||
    run?.exception ||
    "";

  const startedAt =
    run?.started_at || run?.startedAt || run?.created_at || run?.createdAt || "";

  const completedAt =
    run?.completed_at || run?.completedAt || run?.finished_at || run?.finishedAt || "";

  const statusClass = useMemo(() => {
    if (status.includes("SUCCESS") || status.includes("COMPLETED")) {
      return "bg-green-100 text-green-700 border-green-200";
    }
    if (status.includes("FAILED") || status.includes("ERROR")) {
      return "bg-red-100 text-red-700 border-red-200";
    }
    if (status.includes("RUNNING") || status.includes("PENDING")) {
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    }
    return "bg-gray-100 text-gray-700 border-gray-200";
  }, [status]);

  const formatDate = (value: any) => {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
  };

  const pretty = (value: any) => {
    if (value === null || value === undefined || value === "") return "-";
    if (typeof value === "string") {
      try {
        return JSON.stringify(JSON.parse(value), null, 2);
      } catch {
        return value;
      }
    }
    return JSON.stringify(value, null, 2);
  };

  const retryRun = async () => {
    if (!workflowId) {
      setRetryMsg("Retry failed: workflow_id missing in this run.");
      return;
    }

    setRetrying(true);
    setRetryMsg("");

    try {
      const data = await apiRequest<AnyObj>(`/api/workflows/${workflowId}/run`, {
        method: "POST",
        body: JSON.stringify({
          trigger_payload: triggerPayload || {},
          payload: triggerPayload || {},
          retry_of_run_id: runId,
        }),
      });
      const newId = data?.id || data?.run_id || data?.workflow_run_id;

      setRetryMsg(
        newId
          ? `Retry started successfully. New run ID: ${newId}`
          : "Retry started successfully."
      );
    } catch (err: any) {
      setRetryMsg(err instanceof ApiError ? err.detail : err?.message || "Retry failed.");
    } finally {
      setRetrying(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-sm text-gray-500">Loading workflow run...</div>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="p-6 space-y-4">
        <Link href="/admin/workflow-runs" className="text-sm text-blue-600">
          ← Back to Workflow Runs
        </Link>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error || "Workflow run not found."}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <Link href="/admin/workflow-runs" className="text-sm text-blue-600">
            ← Back to Workflow Runs
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-gray-900">
            Workflow Run Detail
          </h1>
          <p className="text-sm text-gray-500">Run ID: {runId}</p>
        </div>

        <button
          onClick={retryRun}
          disabled={retrying}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {retrying ? "Retrying..." : "Retry"}
        </button>
      </div>

      {retryMsg && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-700">
          {retryMsg}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <InfoCard label="Workflow Name" value={workflowName} />
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <div className="text-sm text-gray-500">Status</div>
          <div className={`mt-2 inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${statusClass}`}>
            {status}
          </div>
        </div>
        <InfoCard label="Started At" value={formatDate(startedAt)} />
        <InfoCard label="Completed At" value={formatDate(completedAt)} />
      </div>

      {errorMessage && (
        <section className="rounded-xl border border-red-200 bg-red-50 p-4">
          <h2 className="mb-2 text-lg font-semibold text-red-800">
            Error Message
          </h2>
          <pre className="whitespace-pre-wrap break-words text-sm text-red-700">
            {pretty(errorMessage)}
          </pre>
        </section>
      )}

      <section className="rounded-xl border bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">
          Trigger Payload
        </h2>
        <pre className="max-h-[420px] overflow-auto rounded-lg bg-gray-950 p-4 text-sm text-gray-100">
          {pretty(triggerPayload)}
        </pre>
      </section>

      <section className="rounded-xl border bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">
          Execution Logs
        </h2>
        <pre className="max-h-[520px] overflow-auto rounded-lg bg-gray-950 p-4 text-sm text-gray-100">
          {pretty(executionLogs)}
        </pre>
      </section>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: any }) {
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-1 break-words text-base font-medium text-gray-900">
        {value || "-"}
      </div>
    </div>
  );
}
