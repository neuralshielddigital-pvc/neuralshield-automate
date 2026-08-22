"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError } from "@/lib/api";
import {
  activateWorkflow,
  createWorkflow,
  deactivateWorkflow,
  deleteWorkflow,
  getWorkflowRuns,
  getWorkflows,
  runWorkflowNow,
  updateWorkflow,
  workflowWebhookUrl,
} from "@/lib/workflows";
import type { Workflow, WorkflowActionType, WorkflowRun, WorkflowTriggerType } from "@/lib/types";
import { Workflow as WorkflowIcon } from "lucide-react";

type BuilderForm = {
  name: string;
  description: string;
  triggerType: WorkflowTriggerType;
  actionType: WorkflowActionType;
  webhookUrl: string;
  leadEmail: string;
  leadName: string;
  slackWebhookUrl: string;
  slackMessage: string;
  leadPhone: string;
  leadTags: string;
  auditAction: string;
  spreadsheetId: string;
  sheetName: string;
  emailTo: string;
  emailSubject: string;
  emailBody: string;
  triggerFromEmail: string;
  triggerSubjectContains: string;
  scheduleCron: string;
  channel: string;
  message: string;
  aiPrompt: string;
  aiModel: string;
};

type ActionDraft = {
  id: string;
  type: WorkflowActionType;
  config: Record<string, unknown>;
  trueBranch?: ActionDraft[];
  falseBranch?: ActionDraft[];
};

type SetupRequirement = {
  key: string;
  actionIndex: number;
  actionType: WorkflowActionType;
  title: string;
  description: string;
  complete: boolean;
};

type QuickStartPreset = {
  id: string;
  title: string;
  description: string;
  triggerType: WorkflowTriggerType;
  actions: Array<{
    type: WorkflowActionType;
    config: Record<string, unknown>;
  }>;
};

type WorkflowBuilderDraft = {
  version: 1;
  workflowId: string | null;
  form: BuilderForm;
  actionDrafts: ActionDraft[];
  savedAt: string;
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
  spreadsheetId: "",
  sheetName: "Sheet1",
  slackWebhookUrl: "",
  slackMessage: "New workflow event: {{name}} {{email}}",
  emailTo: "{{email}}",
  emailSubject: "Thanks for contacting us",
  emailBody: "Hello {{name}}, we received your request.",
  triggerFromEmail: "",
  triggerSubjectContains: "",
  scheduleCron: "0 */6 * * *",
  channel: "",
  message: "🚀 New workflow event\nName: {{name}}\nEmail: {{email}}",
  aiPrompt: "Summarize this workflow payload: {{text}} {{email}} {{name}}",
  aiModel: "gpt-4o-mini",
};

const triggerLabels: Record<WorkflowTriggerType, string> = {
  WEBHOOK_RECEIVED: "Webhook received",
  NEW_LEAD: "New lead",
  CAMPAIGN_ACTIVATED: "Campaign activated",
  SCHEDULED: "Scheduled",
  GMAIL_NEW_EMAIL: "Gmail new email",
  SLACK_NEW_MESSAGE: "Slack new message",
};

const actionLabels: Record<WorkflowActionType, string> = {
  SEND_WEBHOOK: "Send webhook",
  SEND_EMAIL: "Send email",
  CREATE_LEAD: "Create lead",
  TAG_LEAD: "Tag lead",
  UPDATE_LEAD: "Update lead",
  HTTP_REQUEST: "HTTP request",
  GOOGLE_SHEETS_APPEND: "Google Sheets append",
  SLACK_SEND_MESSAGE: "Slack message",
  WAIT: "Wait",
  CONDITION: "Condition",
  ADD_AUDIT_LOG: "Add audit log",
  OPENAI_TEXT_GENERATE: "OpenAI text generate",
};

const quickStartPresets: QuickStartPreset[] = [
  {
    id: "gmail-slack",
    title: "Gmail to Slack",
    description:
      "Send a Slack notification whenever a matching Gmail message arrives.",
    triggerType: "GMAIL_NEW_EMAIL",
    actions: [
      {
        type: "SLACK_SEND_MESSAGE",
        config: {
          channel: "",
          message:
            "New email received\nFrom: {{from}}\nSubject: {{subject}}\n{{snippet}}",
        },
      },
    ],
  },
  {
    id: "lead-sheets",
    title: "Lead to Google Sheets",
    description:
      "Capture a new lead and append the details to a Google Sheet.",
    triggerType: "NEW_LEAD",
    actions: [
      {
        type: "GOOGLE_SHEETS_APPEND",
        config: {
          spreadsheet_id: "",
          sheet_name: "Leads",
        },
      },
    ],
  },
  {
    id: "ai-email-summary",
    title: "AI Email Summary",
    description:
      "Summarize incoming Gmail messages with AI and send the result to Slack.",
    triggerType: "GMAIL_NEW_EMAIL",
    actions: [
      {
        type: "OPENAI_TEXT_GENERATE",
        config: {
          model: "gpt-4o-mini",
          prompt:
            "Summarize this email in 3 concise bullet points: {{subject}} {{body}} {{snippet}}",
          temperature: 0.3,
          max_tokens: 500,
        },
      },
      {
        type: "SLACK_SEND_MESSAGE",
        config: {
          channel: "",
          message: "AI email summary:\n{{ai_output}}",
        },
      },
    ],
  },
  {
    id: "webhook-lead",
    title: "Webhook Lead Capture",
    description:
      "Receive lead data through a webhook and create a lead automatically.",
    triggerType: "WEBHOOK_RECEIVED",
    actions: [
      {
        type: "CREATE_LEAD",
        config: {},
      },
      {
        type: "ADD_AUDIT_LOG",
        config: {
          action: "lead.created.from_webhook",
        },
      },
    ],
  },
];

function toErrorMessage(value: unknown, fallback = "Something went wrong.") {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") return JSON.stringify(value);
  return fallback;
}

function hasConfiguredValue(value: unknown) {
  return typeof value === "string" && value.trim().length > 0;
}

function parseWorkflowBuilderDraft(
  value: string | null
): WorkflowBuilderDraft | null {
  if (!value) {
    return null;
  }

  try {
    const parsed: unknown = JSON.parse(value);

    if (
      !parsed ||
      typeof parsed !== "object" ||
      !("version" in parsed) ||
      parsed.version !== 1 ||
      !("form" in parsed) ||
      !parsed.form ||
      typeof parsed.form !== "object" ||
      !("actionDrafts" in parsed) ||
      !Array.isArray(parsed.actionDrafts) ||
      !("savedAt" in parsed) ||
      typeof parsed.savedAt !== "string"
    ) {
      return null;
    }

    return parsed as WorkflowBuilderDraft;
  } catch {
    return null;
  }
}

function workflowRunError(run: WorkflowRun) {
  const steps = run.logs?.steps ?? [];
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
  const searchParams = useSearchParams();
  const actionEditorRef = useRef<HTMLDivElement | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<BuilderForm>(blankForm);
  const [actionDrafts, setActionDrafts] = useState<ActionDraft[]>([]);
  const [editingActionIndex, setEditingActionIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [availableDraft, setAvailableDraft] =
    useState<WorkflowBuilderDraft | null>(null);
  const [draftSavedAt, setDraftSavedAt] = useState<string | null>(null);
  const [hydratedDraftKey, setHydratedDraftKey] =
    useState<string | null>(null);
  const [availableDraftStorageKey, setAvailableDraftStorageKey] =
    useState<string | null>(null);

  const templateWorkflowId = searchParams.get("workflowId");

  const isTemplateSetup = Boolean(templateWorkflowId);

  const draftWorkflowId = editingId ?? templateWorkflowId ?? null;

  const draftStorageKey = draftWorkflowId
    ? `neuralshield:workflow-builder:draft:${draftWorkflowId}`
    : "neuralshield:workflow-builder:draft:new";

  const setupRequirements = useMemo<SetupRequirement[]>(() => {
    return actionDrafts.flatMap<SetupRequirement>(
      (action, actionIndex): SetupRequirement[] => {
      const config = action.config ?? {};

      if (action.type === "SLACK_SEND_MESSAGE") {
        const channel =
          hasConfiguredValue(config.channel) ||
          hasConfiguredValue(config.channel_id);

        const messageConfigured =
          hasConfiguredValue(config.message) ||
          hasConfiguredValue(config.text);

        return [
          {
            key: `${action.id}-slack`,
            actionIndex,
            actionType: action.type,
            title: "Configure Slack message",
            description:
              channel && messageConfigured
                ? "Slack channel and message are configured."
                : "Add a Slack channel or channel ID and confirm the message.",
            complete: channel && messageConfigured,
          },
        ];
      }

      if (action.type === "GOOGLE_SHEETS_APPEND") {
        const spreadsheetConfigured =
          hasConfiguredValue(config.spreadsheet_id);

        const sheetConfigured =
          hasConfiguredValue(config.sheet_name);

        return [
          {
            key: `${action.id}-sheets`,
            actionIndex,
            actionType: action.type,
            title: "Configure Google Sheets",
            description:
              spreadsheetConfigured && sheetConfigured
                ? "Spreadsheet ID and sheet name are configured."
                : "Add the destination Spreadsheet ID and sheet name.",
            complete: spreadsheetConfigured && sheetConfigured,
          },
        ];
      }

      if (action.type === "SEND_EMAIL") {
        const recipientConfigured = hasConfiguredValue(config.to);
        const subjectConfigured = hasConfiguredValue(config.subject);
        const bodyConfigured = hasConfiguredValue(config.body);

        return [
          {
            key: `${action.id}-email`,
            actionIndex,
            actionType: action.type,
            title: "Configure email",
            description:
              recipientConfigured && subjectConfigured && bodyConfigured
                ? "Recipient, subject, and email body are configured."
                : "Confirm the recipient, subject, and email body.",
            complete:
              recipientConfigured && subjectConfigured && bodyConfigured,
          },
        ];
      }

      if (action.type === "SEND_WEBHOOK") {
        const urlConfigured = hasConfiguredValue(config.url);

        return [
          {
            key: `${action.id}-webhook`,
            actionIndex,
            actionType: action.type,
            title: "Configure webhook",
            description: urlConfigured
              ? "Destination webhook URL is configured."
              : "Add the destination webhook URL.",
            complete: urlConfigured,
          },
        ];
      }

      if (action.type === "OPENAI_TEXT_GENERATE") {
        const promptConfigured = hasConfiguredValue(config.prompt);
        const modelConfigured = hasConfiguredValue(config.model);

        return [
          {
            key: `${action.id}-openai`,
            actionIndex,
            actionType: action.type,
            title: "Configure AI generation",
            description:
              promptConfigured && modelConfigured
                ? "AI prompt and model are configured."
                : "Confirm the AI prompt and model.",
            complete: promptConfigured && modelConfigured,
          },
        ];
      }

      return [];
    }
    );
  }, [actionDrafts]);

  const completedSetupCount = setupRequirements.filter(
    (requirement) => requirement.complete
  ).length;

  const missingSetupCount =
    setupRequirements.length - completedSetupCount;

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    setHydratedDraftKey(null);

    let recoveredStorageKey = draftStorageKey;
    let storedDraft = parseWorkflowBuilderDraft(
      window.localStorage.getItem(draftStorageKey)
    );

    if (!storedDraft && !editingId && !templateWorkflowId) {
      const draftPrefix = "neuralshield:workflow-builder:draft:";

      const latestDraft = Object.keys(window.localStorage)
        .filter((key) => key.startsWith(draftPrefix))
        .map((key) => ({
          key,
          draft: parseWorkflowBuilderDraft(
            window.localStorage.getItem(key)
          ),
        }))
        .filter(
          (
            item
          ): item is {
            key: string;
            draft: WorkflowBuilderDraft;
          } => item.draft !== null
        )
        .sort(
          (a, b) =>
            new Date(b.draft.savedAt).getTime() -
            new Date(a.draft.savedAt).getTime()
        )[0];

      if (latestDraft) {
        recoveredStorageKey = latestDraft.key;
        storedDraft = latestDraft.draft;
      }
    }

    setAvailableDraft(storedDraft);
    setAvailableDraftStorageKey(
      storedDraft ? recoveredStorageKey : null
    );
    setDraftSavedAt(storedDraft?.savedAt ?? null);
    setHydratedDraftKey(draftStorageKey);
  }, [draftStorageKey, editingId, templateWorkflowId]);

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      loading ||
      saving ||
      availableDraft ||
      hydratedDraftKey !== draftStorageKey
    ) {
      return;
    }

    const hasDraftContent =
      form.name.trim().length > 0 ||
      form.description.trim().length > 0 ||
      actionDrafts.length > 0 ||
      Boolean(editingId);

    if (!hasDraftContent) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      const draft: WorkflowBuilderDraft = {
        version: 1,
        workflowId: draftWorkflowId,
        form,
        actionDrafts,
        savedAt: new Date().toISOString(),
      };

      try {
        window.localStorage.setItem(
          draftStorageKey,
          JSON.stringify(draft)
        );

        setDraftSavedAt(draft.savedAt);
        setError("");
      } catch {
        setError(
          "Draft could not be saved in this browser. Please save the workflow manually."
        );
      }
    }, 1200);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [
    actionDrafts,
    availableDraft,
    draftStorageKey,
    draftWorkflowId,
    editingId,
    form,
    hydratedDraftKey,
    loading,
    saving,
  ]);

  const selectedWorkflow = useMemo(
    () => workflows.find((workflow) => workflow.id === selectedId) ?? workflows[0] ?? null,
    [selectedId, workflows]
  );

  function applyQuickStartPreset(preset: QuickStartPreset) {
    const drafts: ActionDraft[] = preset.actions.map((action, index) => ({
      id: `quick-start-${preset.id}-${Date.now()}-${index}`,
      type: action.type,
      config: { ...action.config },
    }));

    const firstAction = preset.actions[0];

    setEditingId(null);
    setSelectedId(null);
    setEditingActionIndex(null);
    setAvailableDraft(null);
    setAvailableDraftStorageKey(null);
    setDraftSavedAt(null);
    setError("");

    setForm({
      ...blankForm,
      name: preset.title,
      description: preset.description,
      triggerType: preset.triggerType,
      actionType: firstAction?.type ?? "ADD_AUDIT_LOG",
      channel:
        typeof firstAction?.config.channel === "string"
          ? firstAction.config.channel
          : "",
      message:
        typeof firstAction?.config.message === "string"
          ? firstAction.config.message
          : blankForm.message,
      spreadsheetId:
        typeof firstAction?.config.spreadsheet_id === "string"
          ? firstAction.config.spreadsheet_id
          : "",
      sheetName:
        typeof firstAction?.config.sheet_name === "string"
          ? firstAction.config.sheet_name
          : "Sheet1",
      aiPrompt:
        typeof firstAction?.config.prompt === "string"
          ? firstAction.config.prompt
          : blankForm.aiPrompt,
      aiModel:
        typeof firstAction?.config.model === "string"
          ? firstAction.config.model
          : blankForm.aiModel,
      auditAction:
        typeof firstAction?.config.action === "string"
          ? firstAction.config.action
          : blankForm.auditAction,
    });

    setActionDrafts(drafts);
    setMessage(
      `${preset.title} added to the builder. Review the required settings before saving.`
    );

    window.requestAnimationFrame(() => {
      actionEditorRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }

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
      .catch((err) => setError(err instanceof ApiError ? toErrorMessage(err.detail) : "Could not load workflows."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
  const workflowId = searchParams.get("workflowId");

  if (!workflowId || workflows.length === 0) {
    return;
  }

  const workflow = workflows.find((item) => item.id === workflowId);

  if (!workflow) {
    return;
  }

  startEdit(workflow);

  setMessage("Template loaded. Customize it before activating.");
}, [searchParams, workflows]);

  useEffect(() => {
    const workflowId = selectedWorkflow?.id;
    if (!workflowId) {
      setRuns([]);
      return;
    }
    loadRuns(workflowId).catch((err) => setError(err instanceof ApiError ? toErrorMessage(err.detail) : "Could not load workflow runs."));
  }, [selectedWorkflow?.id]);

  function actionConfig() {
    if (form.actionType === "GOOGLE_SHEETS_APPEND") {
    return {
      spreadsheet_id: form.spreadsheetId,
      sheet_name: form.sheetName || "Sheet1",
    };
  }

    if (form.actionType === "OPENAI_TEXT_GENERATE") {
    return {
      prompt: form.aiPrompt,
      model: form.aiModel || "gpt-4o-mini",
      temperature: 0.3,
      max_tokens: 500,
    };
  }

  if (form.actionType === "SEND_WEBHOOK") {
      return { url: form.webhookUrl };
    }
     if (form.actionType === "SEND_EMAIL") {
  return {
    to: form.emailTo,
    subject: form.emailSubject,
    body: form.emailBody,
  };
}

if (form.actionType === "CONDITION") {
  return {
    field: "email",
    operator: "contains",
    value: "@gmail.com",
  };
}

if (form.actionType === "SLACK_SEND_MESSAGE") {
  return {
    channel: form.channel,
    message: form.message,
  };
}

if (form.actionType === "CREATE_LEAD") {
  return {};
}
  return { action: form.auditAction };
}

function actionSaveType(): WorkflowActionType {
  return form.actionType;
}

  function actionTitle(type: unknown) {
  return typeof type === "string" ? actionLabels[type as WorkflowActionType] ?? type : "Action";
}

function actionDraftSummary(action: ActionDraft) {
  if (action.type === "GOOGLE_SHEETS_APPEND") {
    return typeof action.config.sheet_name === "string" ? ` → ${action.config.sheet_name}` : "";
  }
  if (action.type === "SEND_WEBHOOK") {
    return typeof action.config.url === "string" ? ` → ${action.config.url}` : "";
  }
  if (action.type === "SEND_EMAIL") {
    return typeof action.config.to === "string" ? ` → ${action.config.to}` : "";
  }
  if (action.type === "ADD_AUDIT_LOG") {
    return typeof action.config.action === "string" ? ` → ${action.config.action}` : "";
  }
  return "";
}


function addBranchAction(index: number, branch: "true" | "false") {
  setActionDrafts((current) =>
    current.map((action, actionIndex) => {
      if (actionIndex !== index || action.type !== "CONDITION") {
        return action;
      }

      const nextAction = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        type: actionSaveType(),
        config: actionConfig(),
      };

      if (branch === "true") {
        return {
          ...action,
          trueBranch: [...(action.trueBranch ?? []), nextAction],
        };
      }

      return {
        ...action,
        falseBranch: [...(action.falseBranch ?? []), nextAction],
      };
    })
  );
}

function addCurrentActionDraft() {
  if (form.actionType === "GOOGLE_SHEETS_APPEND" && !form.spreadsheetId.trim()) {
    setError("Google Sheets Append requires Spreadsheet ID before adding action.");
    return;
  }

  setError("");

  setActionDrafts((current) => [
    ...current,
    {
      id: `${Date.now()}-${current.length}`,
      type: actionSaveType(),
      config: actionConfig(),
    },
  ]);
}


function moveActionUp(index: number) {
  if (index === 0) return;

  setActionDrafts((current) => {
    const next = [...current];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    return next;
  });
}

function moveActionDown(index: number) {
  setActionDrafts((current) => {
    if (index >= current.length - 1) return current;

    const next = [...current];
    [next[index], next[index + 1]] = [next[index + 1], next[index]];
    return next;
  });
}


function editActionDraft(index: number) {
  const action = actionDrafts[index];
  if (!action) return;

  const config = action.config ?? {};

  setError("");
  setMessage("");
  setEditingActionIndex(index);

  setForm((current) => ({
    ...current,
    actionType: action.type,
    spreadsheetId:
      typeof config.spreadsheet_id === "string"
        ? config.spreadsheet_id
        : current.spreadsheetId,
    sheetName:
      typeof config.sheet_name === "string"
        ? config.sheet_name
        : current.sheetName,
    webhookUrl:
      typeof config.url === "string"
        ? config.url
        : current.webhookUrl,
    emailTo:
      typeof config.to === "string"
        ? config.to
        : current.emailTo,
    emailSubject:
      typeof config.subject === "string"
        ? config.subject
        : current.emailSubject,
    emailBody:
      typeof config.body === "string"
        ? config.body
        : current.emailBody,
    auditAction:
      typeof config.action === "string"
        ? config.action
        : current.auditAction,
    channel:
      typeof config.channel === "string"
        ? config.channel
        : typeof config.channel_id === "string"
          ? config.channel_id
          : "",
    message:
      typeof config.message === "string"
        ? config.message
        : typeof config.text === "string"
          ? config.text
          : current.message,
    aiPrompt:
      typeof config.prompt === "string"
        ? config.prompt
        : current.aiPrompt,
    aiModel:
      typeof config.model === "string"
        ? config.model
        : current.aiModel,
    slackWebhookUrl:
      typeof config.webhook_url === "string"
        ? config.webhook_url
        : "",
    slackMessage:
      typeof config.message === "string"
        ? config.message
        : current.slackMessage,
  }));

  window.requestAnimationFrame(() => {
    actionEditorRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  });
}

function removeActionDraft(index: number) {
  setActionDrafts((current) =>
    current.filter((_, currentIndex) => currentIndex !== index)
  );

  setEditingActionIndex((currentIndex) => {
    if (currentIndex === null) {
      return null;
    }

    if (currentIndex === index) {
      return null;
    }

    return currentIndex > index ? currentIndex - 1 : currentIndex;
  });
}

function clearActionDrafts() {
  setActionDrafts([]);
  setEditingActionIndex(null);
}


function updateCurrentActionDraft() {
  if (editingActionIndex === null) {
    return;
  }

  if (
    form.actionType === "GOOGLE_SHEETS_APPEND" &&
    !form.spreadsheetId.trim()
  ) {
    setError("Google Sheets Append requires Spreadsheet ID.");
    return;
  }

  if (
    form.actionType === "SLACK_SEND_MESSAGE" &&
    !form.channel.trim()
  ) {
    setError("Slack message requires a channel or channel ID.");
    return;
  }

  if (
    form.actionType === "SEND_WEBHOOK" &&
    !form.webhookUrl.trim()
  ) {
    setError("Send Webhook requires a destination URL.");
    return;
  }

  setError("");

  setActionDrafts((current) =>
    current.map((action, index) =>
      index === editingActionIndex
        ? {
            ...action,
            type: actionSaveType(),
            config: actionConfig(),
          }
        : action
    )
  );

  setEditingActionIndex(null);
  setMessage("Action updated. Click Update workflow to save all changes.");
}

function cancelActionEdit() {
  setEditingActionIndex(null);
  setError("");
  setMessage("Action edit cancelled.");
}

function serializeActionDraft(action: ActionDraft): { type: WorkflowActionType; config: Record<string, unknown> } {
  const config =
    action.type === "CONDITION"
      ? {
          ...action.config,
          on_true: (action.trueBranch ?? []).map(serializeActionDraft),
          on_false: (action.falseBranch ?? []).map(serializeActionDraft),
        }
      : action.config;

  return {
    type: action.type,
    config,
  };
}

function deserializeActionDraft(
  action: {
    type: WorkflowActionType;
    config?: Record<string, unknown>;
  },
  index: number
): ActionDraft {
  const rawConfig = action.config ?? {};

  const trueActions = Array.isArray(rawConfig.on_true)
    ? rawConfig.on_true
    : [];

  const falseActions = Array.isArray(rawConfig.on_false)
    ? rawConfig.on_false
    : [];

  const {
    on_true: _onTrue,
    on_false: _onFalse,
    ...config
  } = rawConfig;

  return {
    id: `loaded-${index}-${Date.now()}-${Math.random()
      .toString(36)
      .slice(2, 8)}`,
    type: action.type,
    config,
    trueBranch: trueActions
      .filter(
        (
          item
        ): item is {
          type: WorkflowActionType;
          config?: Record<string, unknown>;
        } =>
          Boolean(
            item &&
              typeof item === "object" &&
              "type" in item &&
              typeof item.type === "string"
          )
      )
      .map((item, branchIndex) =>
        deserializeActionDraft(item, branchIndex)
      ),
    falseBranch: falseActions
      .filter(
        (
          item
        ): item is {
          type: WorkflowActionType;
          config?: Record<string, unknown>;
        } =>
          Boolean(
            item &&
              typeof item === "object" &&
              "type" in item &&
              typeof item.type === "string"
          )
      )
      .map((item, branchIndex) =>
        deserializeActionDraft(item, branchIndex)
      ),
  };
}

function restoreAvailableDraft() {
  if (!availableDraft) {
    return;
  }

  const restoredDraft = availableDraft;
  const restoredStorageKey = availableDraftStorageKey;

  if (typeof window !== "undefined" && restoredStorageKey) {
    window.localStorage.removeItem(restoredStorageKey);
  }

  setForm(restoredDraft.form);
  setActionDrafts(restoredDraft.actionDrafts);
  setEditingActionIndex(null);

  if (restoredDraft.workflowId) {
    setEditingId(restoredDraft.workflowId);
    setSelectedId(restoredDraft.workflowId);
  }

  setAvailableDraft(null);
  setAvailableDraftStorageKey(null);
  setDraftSavedAt(restoredDraft.savedAt);
  setHydratedDraftKey(draftStorageKey);
  setError("");
  setMessage("Unsaved workflow draft restored.");
}

function discardAvailableDraft() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(
      availableDraftStorageKey ?? draftStorageKey
    );
  }

  setAvailableDraft(null);
  setAvailableDraftStorageKey(null);
  setDraftSavedAt(null);
  setHydratedDraftKey(draftStorageKey);
  setMessage("Saved browser draft discarded.");
  setError("");
}

async function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  setSaving(true);
  setError("");
  setMessage("");

  const triggerConfig =
    form.triggerType === "GMAIL_NEW_EMAIL"
      ? {
          from_email: form.triggerFromEmail.trim(),
          subject_contains: form.triggerSubjectContains.trim(),
        }
      : {};

  const isScheduled = form.triggerType === "SCHEDULED";

  const payload = {
    name: form.name,
    description: form.description || null,
    is_active: false,
    schedule_enabled: isScheduled,
    schedule_cron: isScheduled ? form.scheduleCron : null,
    trigger: { type: form.triggerType, config: triggerConfig },
    actions:
      actionDrafts.length > 0
        ? actionDrafts.map(serializeActionDraft)
        : [{ type: actionSaveType(), config: actionConfig() }],
  };

  try {
    const workflow = editingId
      ? await updateWorkflow(editingId, payload)
      : await createWorkflow(payload);

    if (typeof window !== "undefined") {
      window.localStorage.removeItem(draftStorageKey);
    }

    setAvailableDraft(null);
    setAvailableDraftStorageKey(null);
    setDraftSavedAt(null);
    setSelectedId(workflow.id);
    setEditingId(null);
    setEditingActionIndex(null);
    setActionDrafts([]);
    setForm(blankForm);
    setMessage(editingId ? "Workflow updated." : "Workflow created.");
    await loadWorkflows();
  } catch (err) {
    setError(err instanceof ApiError ? toErrorMessage(err.detail) : "Could not save workflow.");
  } finally {
    setSaving(false);
  }
}

function startEdit(workflow: Workflow) {
  const trigger = workflow.triggers[0];
  const actions = workflow.actions ?? [];
  const firstAction = actions[0];
  const config = firstAction?.config ?? {};
  const triggerConfig = trigger?.config ?? {};

  const loadedDrafts = actions.map((action, index) =>
    deserializeActionDraft(
      {
        type: action.type,
        config: action.config ?? {},
      },
      index
    )
  );

  setEditingId(workflow.id);
  setSelectedId(workflow.id);
  setEditingActionIndex(null);
  setActionDrafts(loadedDrafts);

  setForm({
    name: workflow.name,
    description: workflow.description ?? "",
    triggerType: trigger?.type ?? "WEBHOOK_RECEIVED",
    actionType: firstAction?.type ?? "ADD_AUDIT_LOG",
    webhookUrl:
      typeof config.url === "string"
        ? config.url
        : "",
    leadEmail:
      typeof config.email === "string"
        ? config.email
        : "{{email}}",
    leadName:
      typeof config.name === "string"
        ? config.name
        : "{{name}}",
    leadPhone:
      typeof config.phone === "string"
        ? config.phone
        : "{{phone}}",
    leadTags:
      typeof config.tags === "string"
        ? config.tags
        : "workflow,automation",
    auditAction:
      typeof config.action === "string"
        ? config.action
        : "workflow.action",
    emailTo:
      typeof config.to === "string"
        ? config.to
        : "{{email}}",
    emailSubject:
      typeof config.subject === "string"
        ? config.subject
        : "Thanks for contacting us",
    emailBody:
      typeof config.body === "string"
        ? config.body
        : "Hello {{name}}, we received your request.",
    spreadsheetId:
      typeof config.spreadsheet_id === "string"
        ? config.spreadsheet_id
        : "",
    sheetName:
      typeof config.sheet_name === "string"
        ? config.sheet_name
        : "Sheet1",
    triggerFromEmail:
      typeof triggerConfig.from_email === "string"
        ? triggerConfig.from_email
        : "",
    triggerSubjectContains:
      typeof triggerConfig.subject_contains === "string"
        ? triggerConfig.subject_contains
        : "",
    scheduleCron:
      typeof workflow.schedule_cron === "string"
        ? workflow.schedule_cron
        : "0 */6 * * *",
    slackWebhookUrl:
      typeof config.webhook_url === "string"
        ? config.webhook_url
        : "",
    channel:
      typeof config.channel === "string"
        ? config.channel
        : typeof config.channel_id === "string"
          ? config.channel_id
          : "",
    message:
      typeof config.message === "string"
        ? config.message
        : typeof config.text === "string"
          ? config.text
          : "🚀 New workflow event\nName: {{name}}\nEmail: {{email}}",
    slackMessage:
      typeof config.message === "string"
        ? config.message
        : "New workflow event: {{name}} {{email}}",
    aiPrompt:
      typeof config.prompt === "string"
        ? config.prompt
        : "Summarize this workflow payload: {{text}} {{email}} {{name}}",
    aiModel:
      typeof config.model === "string"
        ? config.model
        : "gpt-4o-mini",
  });
}

async function runWorkflowAction(
  action: () => Promise<unknown>,
  success: string,
  refreshRuns = true
) {
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
    setError(err instanceof ApiError ? toErrorMessage(err.detail) : "Workflow action failed.");
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

      {!loading && workflows.length === 0 && !editingId ? (
        <section className="surface-card border border-sky-200 p-6 sm:p-8">
          <div className="max-w-3xl">
            <p className="page-kicker">Quick start</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">
              Build your first automation
            </h2>
            <p className="mt-2 text-sm leading-6 text-steel">
              Start with a proven workflow, complete the required connection
              details, test it, and activate it when ready.
            </p>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {quickStartPresets.map((preset) => (
              <article
                key={preset.id}
                className="flex h-full flex-col rounded-xl border border-line bg-white p-5 transition hover:-translate-y-0.5 hover:border-pine/30 hover:shadow-panel"
              >
                <div className="flex-1">
                  <p className="text-xs font-semibold uppercase tracking-wide text-pine">
                    {triggerLabels[preset.triggerType]}
                  </p>
                  <h3 className="mt-2 text-base font-semibold text-ink">
                    {preset.title}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-steel">
                    {preset.description}
                  </p>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {preset.actions.map((action, index) => (
                      <span
                        key={`${preset.id}-${action.type}-${index}`}
                        className="status-pill border-line bg-linen text-steel"
                      >
                        {index + 1}. {actionLabels[action.type]}
                      </span>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  className="btn-primary mt-5 w-full"
                  onClick={() => applyQuickStartPreset(preset)}
                >
                  Use this workflow
                </button>
              </article>
            ))}
          </div>

          <div className="mt-5 rounded-xl border border-line bg-linen/70 px-4 py-3 text-sm text-steel">
            Quick Start workflows are created as inactive drafts. No automation
            runs until you review, save, test, and activate it.
          </div>
        </section>
      ) : null}

      {isTemplateSetup && editingId && setupRequirements.length > 0 ? (
        <section className="surface-card border border-amber-200 p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="page-kicker">Template setup</p>
              <h2 className="mt-2 text-xl font-semibold text-ink">
                Complete your workflow setup
              </h2>
              <p className="mt-2 text-sm text-steel">
                Review the required configuration before activating or testing
                this workflow.
              </p>
            </div>

            <div className="rounded-xl border border-line bg-white px-4 py-3 text-sm">
              <p className="font-semibold text-ink">
                {completedSetupCount} of {setupRequirements.length} configured
              </p>
              <p className="mt-1 text-xs text-steel">
                {missingSetupCount === 0
                  ? "Setup is complete."
                  : `${missingSetupCount} item${
                      missingSetupCount === 1 ? "" : "s"
                    } still need attention.`}
              </p>
            </div>
          </div>

          <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-emerald-600 transition-all"
              style={{
                width: `${
                  setupRequirements.length > 0
                    ? Math.round(
                        (completedSetupCount / setupRequirements.length) * 100
                      )
                    : 0
                }%`,
              }}
            />
          </div>

          <div className="mt-5 grid gap-3">
            {setupRequirements.map((requirement) => (
              <div
                key={requirement.key}
                className={`flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center sm:justify-between ${
                  requirement.complete
                    ? "border-emerald-200 bg-emerald-50"
                    : "border-amber-200 bg-amber-50"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      requirement.complete
                        ? "bg-emerald-600 text-white"
                        : "bg-amber-200 text-amber-900"
                    }`}
                  >
                    {requirement.complete ? "✓" : "!"}
                  </div>

                  <div>
                    <p className="font-semibold text-ink">
                      Step {requirement.actionIndex + 1}: {requirement.title}
                    </p>
                    <p className="mt-1 text-sm text-steel">
                      {requirement.description}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  className={
                    requirement.complete
                      ? "btn-secondary shrink-0"
                      : "btn-primary shrink-0"
                  }
                  onClick={() => editActionDraft(requirement.actionIndex)}
                >
                  {requirement.complete ? "Review" : "Configure"}
                </button>
              </div>
            ))}
          </div>

          {missingSetupCount === 0 ? (
            <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              All detected template settings are configured. Save the workflow
              before activating or testing it.
            </div>
          ) : (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Configure each missing item, click Update Action, and then click
              Update workflow to persist all changes.
            </div>
          )}
        </section>
      ) : null}

      {availableDraft ? (
        <section className="surface-card border border-sky-200 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="page-kicker">Draft recovery</p>
              <h2 className="mt-2 text-xl font-semibold text-ink">
                Unsaved workflow draft found
              </h2>
              <p className="mt-2 text-sm text-steel">
                A browser draft was saved{" "}
                {new Date(availableDraft.savedAt).toLocaleString()}.
                Restore it to continue from your previous changes.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                className="btn-primary"
                onClick={restoreAvailableDraft}
              >
                Restore Draft
              </button>

              <button
                type="button"
                className="btn-secondary"
                onClick={discardAvailableDraft}
              >
                Discard Draft
              </button>
            </div>
          </div>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="surface-card p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-ink">
                Visual builder
              </h2>

              {draftSavedAt ? (
                <p className="mt-1 text-xs font-medium text-emerald-700">
                  Draft saved locally at{" "}
                  {new Date(draftSavedAt).toLocaleTimeString()}
                </p>
              ) : (
                <p className="mt-1 text-xs text-steel">
                  Changes are saved locally while you work.
                </p>
              )}
            </div>

            {editingId ? (
              <button
                className="btn-secondary"
                onClick={() => {
                  setEditingId(null);
                  setEditingActionIndex(null);
                  setSelectedId(null);
                  setActionDrafts([]);
                  setForm(blankForm);
                  setMessage("");
                  setError("");
                  setAvailableDraft(null);
                  setDraftSavedAt(null);

                  if (typeof window !== "undefined") {
                    window.localStorage.removeItem(draftStorageKey);
                  }
                }}
                type="button"
              >
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
              <p className="mt-2 text-base font-semibold text-ink">{actionTitle(form.actionType)}</p>
              <p className="mt-2 text-sm text-steel">Runs after the trigger payload has been logged.</p>
            </div>
          </div>

          <form className="mt-6 grid gap-4" onSubmit={handleSubmit}>
            <div ref={actionEditorRef} className="grid gap-4">
              {editingActionIndex !== null ? (
                <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  Editing action step {editingActionIndex + 1}:{" "}
                  {actionTitle(actionDrafts[editingActionIndex]?.type)}
                </div>
              ) : null}

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
{form.triggerType === "GMAIL_NEW_EMAIL" ? (
  <>
    <input
      className="focus-ring px-3.5 py-2.5 text-sm"
      onChange={(event) =>
        setForm((current) => ({ ...current, triggerFromEmail: event.target.value }))
      }
      placeholder="From email contains"
      value={form.triggerFromEmail}
    />
    <input
      className="focus-ring px-3.5 py-2.5 text-sm"
      onChange={(event) =>
        setForm((current) => ({ ...current, triggerSubjectContains: event.target.value }))
      }
      placeholder="Subject contains"
      value={form.triggerSubjectContains}
    />
  </>
) : null}
                <option value="WEBHOOK_RECEIVED">Webhook received</option>
                <option value="SLACK_NEW_MESSAGE">Slack new message</option>
                <option value="NEW_LEAD">New lead</option>
                <option value="CAMPAIGN_ACTIVATED">Campaign activated</option>
                      <option value="SCHEDULED">Scheduled</option>
                <option value="GMAIL_NEW_EMAIL">Gmail new email</option>
              </select>

              {form.triggerType === "GMAIL_NEW_EMAIL" ? (
                <>
                  <input
                    className="focus-ring px-3.5 py-2.5 text-sm"
                    onChange={(event) =>
                      setForm((current) => ({ ...current, triggerFromEmail: event.target.value }))
                    }
                    placeholder="From email contains"
                    value={form.triggerFromEmail}
                  />
                  <input
                    className="focus-ring px-3.5 py-2.5 text-sm"
                    onChange={(event) =>
                      setForm((current) => ({ ...current, triggerSubjectContains: event.target.value }))
                    }
                    placeholder="Subject contains"
                    value={form.triggerSubjectContains}
                  />
                </>
              ) : null}

              {form.triggerType === "SCHEDULED" ? (
  <div className="space-y-4 rounded-xl border border-slate-200 p-4">
    <div>
      <h3 className="text-sm font-semibold text-ink">
        Schedule
      </h3>

      <p className="mt-1 text-xs text-steel">
        Choose how often this workflow should run.
      </p>
    </div>

    {[
      {
        label: "Every 6 hours",
        value: "0 */6 * * *",
      },
      {
        label: "Every 12 hours",
        value: "0 */12 * * *",
      },
      {
        label: "Daily",
        value: "0 0 * * *",
      },
    ].map((item) => (
      <label
        key={item.value}
        className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 hover:bg-slate-50"
      >
        <input
          type="radio"
          name="workflowSchedule"
          checked={form.scheduleCron === item.value}
          onChange={() =>
            setForm((current) => ({
              ...current,
              scheduleCron: item.value,
            }))
          }
        />

        <span className="text-sm font-medium">
          {item.label}
        </span>
      </label>
    ))}

    <p className="text-xs text-steel">
      The workflow starts running automatically after it is activated.
    </p>
  </div>
) : null}

              <select
                className="focus-ring px-3.5 py-2.5 text-sm"
                onChange={(event) => setForm((current) => ({ ...current, actionType: event.target.value as WorkflowActionType }))}
                value={form.actionType}
              >
                <option value="ADD_AUDIT_LOG">Add audit log</option>
                <option value="CREATE_LEAD">Create lead</option>
                <option value="TAG_LEAD">Tag lead</option>
                <option value="UPDATE_LEAD">Update lead</option>
                <option value="SEND_EMAIL">Send email</option>
                <option value="SEND_WEBHOOK">Send webhook</option>
                <option value="HTTP_REQUEST">HTTP request</option>
                <option value="GOOGLE_SHEETS_APPEND">Google Sheets append</option>
                <option value="SLACK_SEND_MESSAGE">Slack message</option>
                <option value="OPENAI_TEXT_GENERATE">OpenAI text generate</option>
                <option value="WAIT">Wait</option>
                <option value="CONDITION">Condition</option>
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
{form.actionType === "SLACK_SEND_MESSAGE" ? (
  <>
    <div className="space-y-2">
      <label className="text-sm font-medium">
        Slack Channel
      </label>

      <input
        className="input"
        placeholder="C0123456789 or #general"
        value={form.channel}
        onChange={(e) =>
          setForm((current) => ({
            ...current,
            channel: e.target.value,
          }))
        }
      />
    </div>

    <div className="space-y-2">
      <label className="text-sm font-medium">
        Message
      </label>

      <textarea
        className="input min-h-[120px]"
        placeholder="Hello from NeuralShield Automation"
        value={form.message}
        onChange={(e) =>
          setForm((current) => ({
            ...current,
            message: e.target.value,
          }))
        }
      />
    </div>
  </>
) : null}

{form.actionType === "OPENAI_TEXT_GENERATE" ? (
  <div className="grid gap-4">
    <input
      className="focus-ring px-3.5 py-2.5 text-sm"
      onChange={(event) =>
        setForm((current) => ({ ...current, aiModel: event.target.value }))
      }
      placeholder="gpt-4o-mini"
      value={form.aiModel}
    />
    <textarea
      className="focus-ring min-h-32 px-3.5 py-2.5 text-sm"
      onChange={(event) =>
        setForm((current) => ({ ...current, aiPrompt: event.target.value }))
      }
      placeholder="Write a prompt using {{text}}, {{email}}, {{name}}"
      required
      value={form.aiPrompt}
    />
  </div>
) : null}

            {form.actionType === "GOOGLE_SHEETS_APPEND" ? (
          <div className="grid gap-4">
            <input
              className="focus-ring px-3.5 py-2.5 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, spreadsheetId: event.target.value }))}
              placeholder="Google Spreadsheet ID"
              required
              value={form.spreadsheetId}
            />
            <input
              className="focus-ring px-3.5 py-2.5 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, sheetName: event.target.value }))}
              placeholder="Sheet1"
              required
              value={form.sheetName}
            />
          </div>
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
            </div>

            {actionDrafts.length > 0 ? (
          <div className="surface-panel p-3 text-sm">
            <p className="font-semibold text-ink">Actions in chain</p>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-steel">
              {actionDrafts.map((action, index) => (
                <li
                  key={action.id}
                  className={`flex items-center justify-between gap-3 rounded-lg px-3 py-2 ${
                    editingActionIndex === index
                      ? "border border-amber-300 bg-amber-50"
                      : ""
                  }`}
                >
                  <span>
                    Step {index + 1}: {actionTitle(action.type)}{actionDraftSummary(action)}

                    {action.type === "CONDITION" ? (
                      <div className="mt-2 flex gap-2">
                        <button
                          type="button"
                          className="btn-secondary px-2 py-1 text-xs"
                          onClick={() => addBranchAction(index, "true")}
                        >
                          + True Action
                        </button>

                        <button
                          type="button"
                          className="btn-secondary px-2 py-1 text-xs"
                          onClick={() => addBranchAction(index, "false")}
                        >
                          + False Action
                        </button>
                      </div>
                    ) : null}
                    {action.type === "CONDITION" && (
                      <div className="mt-3 rounded-lg border border-slate-200 p-3 text-xs">
                        <div className="grid gap-3 md:grid-cols-2">
                          <div>
                            <div className="font-semibold text-green-700">
                              TRUE Branch
                            </div>

                            {action.trueBranch?.length ? (
                              <ul className="mt-2 space-y-1">
                                {action.trueBranch.map((branchAction, branchIndex) => (
                                  <li key={branchAction.id}>
                                    {branchIndex + 1}. {actionTitle(branchAction.type)}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="mt-2 text-slate-400">No actions</p>
                            )}
                          </div>

                          <div>
                            <div className="font-semibold text-red-700">
                              FALSE Branch
                            </div>

                            {action.falseBranch?.length ? (
                              <ul className="mt-2 space-y-1">
                                {action.falseBranch.map((branchAction, branchIndex) => (
                                  <li key={branchAction.id}>
                                    {branchIndex + 1}. {actionTitle(branchAction.type)}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="mt-2 text-slate-400">No actions</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                  </span>

                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="btn-secondary px-2 py-1 text-xs"
                      onClick={() => moveActionUp(index)}
                      disabled={index === 0}
                    >
                      ↑
                    </button>

                    <button
                      type="button"
                      className="btn-secondary px-2 py-1 text-xs"
                      onClick={() => moveActionDown(index)}
                      disabled={index === actionDrafts.length - 1}
                    >
                      ↓
                    </button>

                    <button
                      type="button"
                      className="btn-secondary px-2 py-1 text-xs"
                      onClick={() => editActionDraft(index)}
                    >
                      ✏
                    </button>

                    <button
                      type="button"
                      className="btn-secondary px-2 py-1 text-xs"
                      onClick={() => removeActionDraft(index)}
                    >
                      ✕
                    </button>
                  </div>
                </li>
              ))}
            </ol>
            <button className="btn-secondary mt-3" type="button" onClick={clearActionDrafts}>
              Clear actions
            </button>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-3">
          {editingActionIndex === null ? (
            <button
              className="btn-secondary"
              type="button"
              onClick={addCurrentActionDraft}
            >
              Add Action
            </button>
          ) : (
            <>
              <button
                className="btn-primary"
                type="button"
                onClick={updateCurrentActionDraft}
              >
                Update Action
              </button>

              <button
                className="btn-secondary"
                type="button"
                onClick={cancelActionEdit}
              >
                Cancel Edit
              </button>
            </>
          )}
        </div>

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
        <div>
  <h2 className="text-lg font-semibold text-ink">Your Workflows</h2>
  <p className="mt-1 text-sm text-steel">
    Create, manage, test, and monitor your automation workflows.
  </p>
</div>
        <div className="table-wrap">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase text-steel">
              <tr>
                <th className="py-3 pr-4">Workflow</th>
                <th className="py-3 pr-4">Trigger</th>
                <th className="py-3 pr-4">Steps</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((workflow) => {
                const triggerType = workflow.triggers[0]?.type;
                const scheduleLabel =
                  workflow.schedule_cron === "0 */6 * * *"
                    ? "Every 6 hours"
                    : workflow.schedule_cron === "0 */12 * * *"
                      ? "Every 12 hours"
                      : workflow.schedule_cron === "0 0 * * *"
                        ? "Daily"
                        : null;

                return (
                  <tr className="border-b border-line/70" key={workflow.id}>
                    <td className="py-4 pr-4">
                      <p className="font-semibold text-ink">
                        {workflow.name}
                      </p>

                      <div className="mt-2 flex flex-wrap gap-2">
                        <span
                          className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                            workflow.is_active
                              ? "border-pine/20 bg-mint text-pine"
                              : "border-line bg-slate-50 text-steel"
                          }`}
                        >
                          {workflow.is_active ? "Active" : "Inactive"}
                        </span>

                        {triggerType ? (
                          <span className="rounded-full border border-line bg-white px-2.5 py-1 text-xs font-medium text-steel">
                            {triggerLabels[triggerType]}
                          </span>
                        ) : null}

                        <span className="rounded-full border border-line bg-white px-2.5 py-1 text-xs font-medium text-steel">
                          {workflow.actions.length}{" "}
                          {workflow.actions.length === 1 ? "action" : "actions"}
                        </span>

                        {triggerType === "SCHEDULED" && scheduleLabel ? (
                          <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-medium text-sky-700">
                            {scheduleLabel}
                          </span>
                        ) : null}
                      </div>
                    </td>

                    <td className="py-4 pr-4 text-steel">
                      {triggerType ? triggerLabels[triggerType] : "-"}
                    </td>

                    <td className="py-4 pr-4 text-steel">
                      {workflow.actions.length}
                    </td>

                    <td className="py-4 pr-4">
                      <span
                        className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                          workflow.is_active
                            ? "border-pine/20 bg-mint text-pine"
                            : "border-line bg-slate-50 text-steel"
                        }`}
                      >
                        {workflow.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>

                    <td className="flex flex-wrap gap-2 py-4 pr-4">
                      <button
                        className="btn-secondary px-3 py-1.5 text-xs"
                        onClick={() => {
                          setSelectedId(workflow.id);
                          loadRuns(workflow.id);
                        }}
                        type="button"
                      >
                        Runs
                      </button>

                      <button
                        className="btn-secondary px-3 py-1.5 text-xs"
                        onClick={() =>
                          runWorkflowAction(
                            () => runWorkflowNow(workflow.id),
                            "Workflow test executed."
                          )
                        }
                        type="button"
                      >
                        Run Now
                      </button>

                      <button
                        className="btn-secondary px-3 py-1.5 text-xs"
                        onClick={() => startEdit(workflow)}
                        type="button"
                      >
                        Edit
                      </button>

                      {workflow.is_active ? (
                        <button
                          className="btn-secondary px-3 py-1.5 text-xs"
                          onClick={() =>
                            runWorkflowAction(
                              () => deactivateWorkflow(workflow.id),
                              "Workflow deactivated."
                            )
                          }
                          type="button"
                        >
                          Deactivate
                        </button>
                      ) : (
                        <button
                          className="btn-secondary px-3 py-1.5 text-xs"
                          onClick={() =>
                            runWorkflowAction(
                              () => activateWorkflow(workflow.id),
                              "Workflow activated."
                            )
                          }
                          type="button"
                        >
                          Activate
                        </button>
                      )}

                      <button
                        className="focus-ring rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50"
                        onClick={() =>
                          runWorkflowAction(
                            () => deleteWorkflow(workflow.id),
                            "Workflow deleted.",
                            false
                          )
                        }
                        type="button"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}
              {!loading && workflows.length === 0 ? (
  <tr>
    <td colSpan={5} className="py-10">
      <div className="mx-auto max-w-2xl rounded-3xl border border-dashed border-pine/25 bg-mint/30 p-8 text-center sm:p-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-mint text-pine">
          <WorkflowIcon className="h-7 w-7" aria-hidden="true" />
        </div>

        <h3 className="mt-5 text-xl font-semibold text-ink">
          Create your first workflow
        </h3>

        <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-steel">
          Build an automation from scratch or start faster with a ready-made
          workflow template.
        </p>

        <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
          <button
            className="btn-primary"
            onClick={() => {
              setEditingId(null);
              window.scrollTo({
                top: 0,
                behavior: "smooth",
              });
            }}
            type="button"
          >
            Create Workflow
          </button>

          <button
            className="btn-secondary"
            onClick={() => {
  window.location.href = "/dashboard/templates";
}}
            type="button"
          >
            Browse Templates
          </button>
        </div>
      </div>
    </td>
  </tr>
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
          {runs.length === 0 ? (
  <div className="rounded-2xl border border-dashed border-line bg-slate-50/60 px-6 py-10 text-center">
    <h3 className="text-base font-semibold text-ink">
      No workflow executions yet
    </h3>

    <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-steel">
      Select and run a workflow to view its execution status, activity logs,
      and debugging details here.
    </p>
  </div>
) : null}
        </div>
      </section>
    </div>
  );
}
