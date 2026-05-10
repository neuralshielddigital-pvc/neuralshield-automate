"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  activateWorkflow,
  createWorkflow,
  deactivateWorkflow,
  deleteWorkflow,
  getWorkflowRuns,
  getWorkflows,
  updateWorkflow,
  workflowWebhookUrl
} from "@/lib/workflows";
import type { Workflow, WorkflowActionType, WorkflowRun, WorkflowTriggerType } from "@/lib/types";

type BuilderForm = {
  name: string;
  description: string;
  triggerType: WorkflowTriggerType;
  actionType: WorkflowActionType;
  webhookUrl: string;
  leadEmail: string;
  leadName: string;
  leadPhone: string;
  leadTags: string;
  auditAction: string;
  emailTo: string;
  emailSubject: string;
  emailBody: string;
};

const blankForm: BuilderForm = {
  name: "",
  description: "",
  triggerType: "WEBHOOK_RECEIVED",
  actionType: "ADD_AUDIT_LOG",
  webhookUrl: "",
  leadEmail: "{{email}}",
  leadName: "{{name}}",
  leadPhone: "{{phone}}",
  leadTags: "workflow,automation",
  auditAction: "workflow.action",
  emailTo: "{{email}}",
  emailSubject: "Thanks for contacting us",
  emailBody: "Hello {{name}}, we received your request."
};

const triggerLabels: Record<WorkflowTriggerType, string> = {
  WEBHOOK_RECEIVED: "Webhook received",
  NEW_LEAD: "New lead",
  CAMPAIGN_ACTIVATED: "Campaign activated"
};

const actionLabels: Record<WorkflowActionType, string> = {
  SEND_WEBHOOK: "Send webhook",
  SEND_EMAIL: "Send email",
  CREATE_LEAD: "Create lead",
  ADD_AUDIT_LOG: "Add audit log"
};

function workflowRunError(run: WorkflowRun) {
  const steps = run.logs.steps;
  if (!Array.isArray(steps)) {
    return "";
  }
  const failedStep = steps.find((step) => typeof step === "object" && step !== null && "error" in step);
  if (!failedStep || typeof failedStep !== "object" || failedStep === null || !("error" in failedStep)) {
    return "";
  }
  return String(failedStep.error);
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<BuilderForm>(blankForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedWorkflow = useMemo(
    () => workflows.find((workflow) => workflow.id === selectedId) ?? workflows[0] ?? null,
    [selectedId, workflows]
  );

  async function loadWorkflows() {
    const response = await getWorkflows();
    setWorkflows(response.items);
    if (!selectedId || !response.items.some((workflow) => workflow.id === selectedId)) {
      setSelectedId(response.items[0]?.id ?? null);
    }
  }

  async function loadRuns(workflowId: string) {
    const response = await getWorkflowRuns(workflowId);
    setRuns(response.items);
  }

  useEffect(() => {
    loadWorkflows()
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Could not load workflows."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const workflowId = selectedWorkflow?.id;
    if (!workflowId) {
      setRuns([]);
      return;
    }
    loadRuns(workflowId).catch((err) => setError(err instanceof ApiError ? err.detail : "Could not load workflow runs."));
  }, [selectedWorkflow?.id]);

  function actionConfig() {
    if (form.actionType === "SEND_WEBHOOK") {
      return { url: form.webhookUrl };
    }
    if (form.actionType === "SEND_EMAIL") {
      return {
        to: form.emailTo,
        subject: form.emailSubject,
        body: form.emailBody
      };
    }
    if (form.actionType === "CREATE_LEAD") {
      return {};
    }
    return { action: form.auditAction };
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    const payload = {
      name: form.name,
      description: form.description || null,
      is_active: false,
      trigger: { type: form.triggerType, config: {} },
      actions: [{ type: form.actionType, config: actionConfig() }]
    };

    try {
      const workflow = editingId ? await updateWorkflow(editingId, payload) : await createWorkflow(payload);
      setSelectedId(workflow.id);
      setEditingId(null);
      setForm(blankForm);
      setMessage(editingId ? "Workflow updated." : "Workflow created.");
      await loadWorkflows();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save workflow.");
    } finally {
      setSaving(false);
    }
  }

  function startEdit(workflow: Workflow) {
    const trigger = workflow.triggers[0];
    const action = workflow.actions[0];
    const config = action?.config ?? {};
    setEditingId(workflow.id);
    setSelectedId(workflow.id);
    setForm({
      name: workflow.name,
      description: workflow.description ?? "",
      triggerType: trigger?.type ?? "WEBHOOK_RECEIVED",
      actionType: action?.type ?? "ADD_AUDIT_LOG",
      webhookUrl: typeof config.url === "string" ? config.url : "",
      leadEmail: typeof config.email === "string" ? config.email : "{{email}}",
      leadName: typeof config.name === "string" ? config.name : "{{name}}",
      leadPhone: typeof config.phone === "string" ? config.phone : "{{phone}}",
      leadTags: typeof config.tags === "string" ? config.tags : "workflow,automation",
      auditAction: typeof config.action === "string" ? config.action : "workflow.action",
      emailTo: typeof config.to === "string" ? config.to : "{{email}}",
      emailSubject: typeof config.subject === "string" ? config.subject : "Thanks for contacting us",
      emailBody: typeof config.body === "string" ? config.body : "Hello {{name}}, we received your request."
    });
  }

  async function runWorkflowAction(action: () => Promise<unknown>, success: string, refreshRuns = true) {
    setError("");
    setMessage("");
    try {
      await action();
      setMessage(success);
      await loadWorkflows();
      if (refreshRuns && selectedId) {
        try {
          await loadRuns(selectedId);
        } catch {
          setRuns([]);
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Workflow action failed.");
    }
  }

  async function copyWebhookUrl(workflow: Workflow) {
    await navigator.clipboard.writeText(workflowWebhookUrl(workflow.public_webhook_key));
    setMessage("Webhook URL copied.");
  }

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6 sm:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="page-kicker">Zapier-like automation</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Workflows</h1>
            <p className="mt-2 text-sm text-steel">Connect triggers to actions across webhooks, leads, campaigns, and audit events.</p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="metric-card px-4 py-3">
              <p className="text-lg font-semibold text-ink">{workflows.length}</p>
              <p className="text-xs text-steel">Total</p>
            </div>
            <div className="metric-card px-4 py-3">
              <p className="text-lg font-semibold text-ink">{workflows.filter((workflow) => workflow.is_active).length}</p>
              <p className="text-xs text-steel">Active</p>
            </div>
            <div className="metric-card px-4 py-3">
              <p className="text-lg font-semibold text-ink">{runs.length}</p>
              <p className="text-xs text-steel">Runs</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="surface-card p-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-ink">Visual builder</h2>
            {editingId ? (
              <button className="btn-secondary" onClick={() => { setEditingId(null); setForm(blankForm); }} type="button">
                New workflow
              </button>
            ) : null}
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
            <div className="workflow-node workflow-node-trigger p-4">
              <p className="text-xs font-semibold uppercase text-pine">Trigger</p>
              <p className="mt-2 text-base font-semibold text-ink">{triggerLabels[form.triggerType]}</p>
              <p className="mt-2 text-sm text-steel">Starts when the selected event is received for this tenant.</p>
            </div>
            <div className="hidden h-px w-16 bg-line md:block" />
            <div className="workflow-node workflow-node-action p-4">
              <p className="text-xs font-semibold uppercase text-pine">Action</p>
              <p className="mt-2 text-base font-semibold text-ink">{actionLabels[form.actionType]}</p>
              <p className="mt-2 text-sm text-steel">Runs after the trigger payload has been logged.</p>
            </div>
          </div>

          <form className="mt-6 grid gap-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <input
                className="focus-ring px-3.5 py-2.5 text-sm"
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                placeholder="Workflow name"
                required
                value={form.name}
              />
              <input
                className="focus-ring px-3.5 py-2.5 text-sm"
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                placeholder="Description"
                value={form.description}
              />
              <select
                className="focus-ring px-3.5 py-2.5 text-sm"
                onChange={(event) => setForm((current) => ({ ...current, triggerType: event.target.value as WorkflowTriggerType }))}
                value={form.triggerType}
              >
                <option value="WEBHOOK_RECEIVED">Webhook received</option>
                <option value="NEW_LEAD">New lead</option>
                <option value="CAMPAIGN_ACTIVATED">Campaign activated</option>
              </select>
              <select
                className="focus-ring px-3.5 py-2.5 text-sm"
                onChange={(event) => setForm((current) => ({ ...current, actionType: event.target.value as WorkflowActionType }))}
                value={form.actionType}
              >
                <option value="ADD_AUDIT_LOG">Add audit log</option>
                <option value="SEND_EMAIL">Send email</option>
                <option value="SEND_WEBHOOK">Send webhook</option>
                <option value="CREATE_LEAD">Create lead</option>
              </select>
            </div>

            {form.actionType === "SEND_WEBHOOK" ? (
              <input
                className="focus-ring px-3.5 py-2.5 text-sm"
                onChange={(event) => setForm((current) => ({ ...current, webhookUrl: event.target.value }))}
                placeholder="https://example.com/webhook"
                required
                type="url"
                value={form.webhookUrl}
              />
            ) : null}

            {form.actionType === "SEND_EMAIL" ? (
              <div className="grid gap-4">
                <input
                  className="focus-ring px-3.5 py-2.5 text-sm"
                  onChange={(event) => setForm((current) => ({ ...current, emailTo: event.target.value }))}
                  placeholder="{{email}}"
                  required
                  value={form.emailTo}
                />
                <input
                  className="focus-ring px-3.5 py-2.5 text-sm"
                  onChange={(event) => setForm((current) => ({ ...current, emailSubject: event.target.value }))}
                  placeholder="Thanks for contacting us"
                  required
                  value={form.emailSubject}
                />
                <textarea
                  className="focus-ring min-h-28 px-3.5 py-2.5 text-sm"
                  onChange={(event) => setForm((current) => ({ ...current, emailBody: event.target.value }))}
                  placeholder="Hello {{name}}, we received your request."
                  required
                  value={form.emailBody}
                />
              </div>
            ) : null}

            {form.actionType === "CREATE_LEAD" ? (
              <p className="surface-panel px-3 py-2 text-sm text-steel">
                Uses webhook payload fields: name, email, phone, source, tags.
              </p>
            ) : null}

            {form.actionType === "ADD_AUDIT_LOG" ? (
              <input
                className="focus-ring px-3.5 py-2.5 text-sm"
                onChange={(event) => setForm((current) => ({ ...current, auditAction: event.target.value }))}
                placeholder="workflow.action"
                required
                value={form.auditAction}
              />
            ) : null}

            {message ? <p className="alert-success">{message}</p> : null}
            {error ? <p className="alert-error">{error}</p> : null}
            <button className="btn-primary w-fit" disabled={saving}>
              {saving ? "Saving..." : editingId ? "Update workflow" : "Create workflow"}
            </button>
          </form>
        </div>

        <aside className="surface-card p-6">
          <h2 className="text-lg font-semibold text-ink">Webhook URL</h2>
          {selectedWorkflow ? (
            <div className="mt-4 grid gap-3">
              <p className="surface-panel break-all p-3 text-xs text-steel">
                {workflowWebhookUrl(selectedWorkflow.public_webhook_key)}
              </p>
              <button className="btn-secondary" onClick={() => copyWebhookUrl(selectedWorkflow)} type="button">
                Copy webhook URL
              </button>
            </div>
          ) : (
            <p className="mt-3 text-sm text-steel">Create a workflow to generate a secure public webhook endpoint.</p>
          )}
        </aside>
      </section>

      <section className="surface-card p-6">
        <h2 className="text-lg font-semibold text-ink">Workflow list</h2>
        <div className="table-wrap">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase text-steel">
              <tr>
                <th className="py-3 pr-4">Name</th>
                <th className="py-3 pr-4">Trigger</th>
                <th className="py-3 pr-4">Action</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((workflow) => (
                <tr className="border-b border-line/70" key={workflow.id}>
                  <td className="py-3 pr-4 font-medium text-ink">{workflow.name}</td>
                  <td className="py-3 pr-4 text-steel">{workflow.triggers[0]?.type ?? "-"}</td>
                  <td className="py-3 pr-4 text-steel">{workflow.actions[0]?.type ?? "-"}</td>
                  <td className="py-3 pr-4 text-steel">{workflow.is_active ? "Active" : "Inactive"}</td>
                  <td className="flex flex-wrap gap-2 py-3 pr-4">
                    <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => { setSelectedId(workflow.id); loadRuns(workflow.id); }} type="button">Runs</button>
                    <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => startEdit(workflow)} type="button">Edit</button>
                    {workflow.is_active ? (
                      <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => runWorkflowAction(() => deactivateWorkflow(workflow.id), "Workflow deactivated.")} type="button">Deactivate</button>
                    ) : (
                      <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => runWorkflowAction(() => activateWorkflow(workflow.id), "Workflow activated.")} type="button">Activate</button>
                    )}
                    <button className="focus-ring rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50" onClick={() => runWorkflowAction(() => deleteWorkflow(workflow.id), "Workflow deleted.", false)} type="button">Delete</button>
                  </td>
                </tr>
              ))}
              {!loading && workflows.length === 0 ? (
                <tr><td className="py-5 text-steel" colSpan={5}>No workflows yet.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="surface-card p-6">
        <h2 className="text-lg font-semibold text-ink">Execution logs</h2>
        <div className="mt-4 grid gap-3">
          {runs.map((run) => (
            <div className="surface-panel p-4" key={run.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-ink">{run.status}</p>
                <p className="text-xs text-steel">{new Date(run.created_at).toLocaleString()}</p>
              </div>
              {run.status === "FAILED" && workflowRunError(run) ? (
                <p className="alert-error mt-3">{workflowRunError(run)}</p>
              ) : null}
              <pre className="mt-3 max-h-56 overflow-auto rounded bg-white p-3 text-xs text-steel">
                {JSON.stringify({ trigger_payload: run.trigger_payload, logs: run.logs }, null, 2)}
              </pre>
            </div>
          ))}
          {runs.length === 0 ? <p className="empty-state">No execution logs yet.</p> : null}
        </div>
      </section>
    </div>
  );
}
