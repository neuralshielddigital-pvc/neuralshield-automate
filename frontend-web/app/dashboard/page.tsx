"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiRequest } from "@/lib/api";

type SubscriptionResponse = {
  subscription?: {
    status: string;
    current_period_end?: string | null;
    plan: {
      name: string;
      price: string;
    };
  } | null;
};

type UsageSummary = {
  period: {
    start: string;
    label: string;
  };
  plan: {
    name: string;
    internal_name: string;
    workflow_limit: number;
    monthly_run_limit: number;
    remaining_workflows: number | null;
    remaining_runs: number | null;
  };
  workflows: {
    total: number;
    active: number;
    inactive: number;
  };
  runs: {
    total: number;
    completed: number;
    failed: number;
    running: number;
    queued: number;
    success_rate: number;
  };
  recent_runs: Array<{
    id: string;
    workflow_id: string;
    workflow_name: string;
    status: string;
    created_at: string;
    last_error?: string | null;
  }>;
  top_workflows: Array<{
    id: string;
    name: string;
    is_active: boolean;
    run_count: number;
  }>;
};

type OnboardingStep = {
  title: string;
  completed: boolean;
  href: string;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.detail === "string"
      ? error.detail
      : "Could not load dashboard data.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Could not load dashboard data.";
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatLimit(value: number): string {
  return value === -1 ? "Unlimited" : formatNumber(value);
}

function formatDate(value?: string | null): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
  }).format(date);
}

function formatDateTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function displayStatus(status?: string | null): string {
  if (!status) {
    return "Inactive";
  }

  return status
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusClasses(status: string): string {
  const normalized = status.toUpperCase();

  if (normalized === "COMPLETED" || normalized === "ACTIVE") {
    return "status-pill border-pine/20 bg-mint text-pine";
  }

  if (normalized === "FAILED") {
    return "status-pill border-red-200 bg-red-50 text-red-700";
  }

  if (normalized === "RUNNING") {
    return "status-pill border-sky-200 bg-sky-50 text-sky-700";
  }

  return "status-pill border-line bg-white text-steel";
}

export default function DashboardPage() {
  const [subscription, setSubscription] =
    useState<SubscriptionResponse | null>(null);

  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [slackConnected, setSlackConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const [subscriptionResult, usageResult] = await Promise.all([
        apiRequest<SubscriptionResponse>("/api/billing/subscription"),
        apiRequest<UsageSummary>("/api/workflows/usage-summary"),
      ]);

      setSubscription(subscriptionResult);
      setUsage(usageResult);

      const [gmailResult, slackResult] = await Promise.allSettled([
        apiRequest("/api/integrations/google/gmail/profile"),
        apiRequest("/api/integrations/slack/profile"),
      ]);

      setGmailConnected(gmailResult.status === "fulfilled");
      setSlackConnected(slackResult.status === "fulfilled");
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const subscriptionPlan =
    subscription?.subscription?.plan?.name?.toLowerCase() === "enterprise"
      ? "Business"
      : subscription?.subscription?.plan?.name;

  const plan =
    usage?.plan.name ??
    subscriptionPlan ??
    "Free";

  const status = displayStatus(
    subscription?.subscription?.status,
  );

  const renewalDate = formatDate(
    subscription?.subscription?.current_period_end,
  );

  const workflowUsagePercent = useMemo(() => {
    if (!usage || usage.plan.workflow_limit === -1) {
      return 0;
    }

    if (usage.plan.workflow_limit <= 0) {
      return 0;
    }

    return Math.min(
      Math.round(
        (usage.workflows.total / usage.plan.workflow_limit) * 100,
      ),
      100,
    );
  }, [usage]);

  const runUsagePercent = useMemo(() => {
    if (!usage || usage.plan.monthly_run_limit === -1) {
      return 0;
    }

    if (usage.plan.monthly_run_limit <= 0) {
      return 0;
    }

    return Math.min(
      Math.round(
        (usage.runs.total / usage.plan.monthly_run_limit) * 100,
      ),
      100,
    );
  }, [usage]);

  const metricCards = usage
    ? [
        {
          label: "Active Workflows",
          value: formatNumber(usage.workflows.active),
          detail: `${formatNumber(usage.workflows.total)} total workflows`,
        },
        {
          label: `${usage.period.label} Runs`,
          value: formatNumber(usage.runs.total),
          detail: `${formatNumber(
            usage.plan.remaining_runs ?? 0,
          )} remaining`,
        },
        {
          label: "Success Rate",
          value: `${usage.runs.success_rate.toFixed(1)}%`,
          detail: `${formatNumber(
            usage.runs.completed,
          )} completed runs`,
        },
        {
          label: "Failed Runs",
          value: formatNumber(usage.runs.failed),
          detail:
            usage.runs.failed > 0
              ? "Review recent failures"
              : "No failures this month",
        },
      ]
    : [];

const onboardingSteps: OnboardingStep[] = [
  {
    title: "Connect Gmail or Slack",
    completed: gmailConnected || slackConnected,
    href: "/dashboard/integrations",
  },
  {
    title: "Create your first workflow",
    completed: (usage?.workflows.total ?? 0) > 0,
    href: "/dashboard/workflows",
  },
  {
    title: "Run your first automation",
    completed: (usage?.runs.total ?? 0) > 0,
    href: "/dashboard/workflows",
  },
  {
    title: "Upgrade when you're ready",
    completed: plan !== "Free",
    href: "/dashboard/billing",
  },
];

const completedSteps = onboardingSteps.filter(
  (step) => step.completed,
).length;

  return (
    <div className="grid gap-7">
      <section className="surface-card overflow-hidden p-6 sm:p-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_340px] lg:items-end">
          <div>
            <p className="page-kicker">Workspace overview</p>

            <h1 className="mt-2 text-3xl font-bold text-ink sm:text-4xl">
              Automation Dashboard
            </h1>

            <p className="mt-3 max-w-2xl text-sm leading-6 text-steel">
              Track workflow activity, monthly usage, execution health, and
              plan capacity from one workspace.
            </p>

            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href="/dashboard/workflows"
                className="btn-primary"
              >
                Create workflow
              </Link>

              <Link
                href="/dashboard/integrations"
                className="btn-secondary"
              >
                Manage integrations
              </Link>

              <button
                type="button"
                className="btn-secondary"
                disabled={loading || refreshing}
                onClick={() => void loadDashboard(true)}
              >
                {refreshing ? "Refreshing..." : "Refresh usage"}
              </button>
            </div>
          </div>

          <div className="surface-panel p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-pine">
                  Current plan
                </p>

                <p className="mt-2 text-2xl font-bold text-ink">
                  {loading ? "Loading..." : plan}
                </p>
              </div>

              {!loading ? (
                <span
                  className={statusClasses(
                    subscription?.subscription?.status ?? "INACTIVE",
                  )}
                >
                  {status}
                </span>
              ) : null}
            </div>

            <p className="mt-3 text-sm text-steel">
              Renewal: {loading ? "Loading..." : renewalDate}
            </p>

            <p className="mt-1 text-sm text-steel">
              Workflow limit:{" "}
              {usage
                ? formatLimit(usage.plan.workflow_limit)
                : "Loading..."}
            </p>

            <p className="mt-1 text-sm text-steel">
              Monthly run limit:{" "}
              {usage
                ? formatLimit(usage.plan.monthly_run_limit)
                : "Loading..."}
            </p>

            <Link
              href="/dashboard/billing"
              className="btn-primary mt-4 inline-block w-full text-center"
            >
              {plan === "Free" ? "Upgrade plan" : "Manage plan"}
            </Link>
          </div>
        </div>
      </section>

<section className="surface-card border border-pine/20 bg-mint/40 p-6">
  <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p className="page-kicker">Getting Started</p>

      <h2 className="mt-2 text-2xl font-bold text-ink">
        Complete your first automation
      </h2>

      <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
        Most customers are up and running in less than 5 minutes.
        Complete these steps to activate your workspace.
      </p>

      <div className="mt-4 text-sm font-semibold text-pine">
        {completedSteps} of {onboardingSteps.length} completed
      </div>

      <div
        className="mt-3 h-2.5 max-w-xl overflow-hidden rounded-full bg-white"
        aria-label="Onboarding progress"
      >
        <div
          className="h-full rounded-full bg-emerald-600 transition-all"
          style={{
            width: `${
              (completedSteps / onboardingSteps.length) * 100
            }%`,
          }}
        />
      </div>
    </div>

    <Link
      href="/dashboard/templates"
      className="btn-primary"
    >
      Browse templates
    </Link>
  </div>

  <div className="mt-6 grid gap-3">
    {onboardingSteps.map((step) => (
      <Link
        key={step.title}
        href={step.href}
        className="flex items-center justify-between rounded-xl border border-line bg-white px-5 py-4 transition hover:border-pine/30"
      >
        <div className="flex items-center gap-3">
          <span
            className={`flex h-8 w-8 items-center justify-center rounded-full font-bold ${
              step.completed
                ? "bg-mint text-pine"
                : "bg-linen text-steel"
            }`}
          >
            {step.completed ? "✓" : "•"}
          </span>

          <span className="font-medium text-ink">
            {step.title}
          </span>
        </div>

        <span className="text-sm font-semibold text-pine">
          {step.completed ? "Completed" : "Open"}
        </span>
      </Link>
    ))}
  </div>
</section>

      {error ? (
        <section className="alert-error flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span>{error}</span>

          <button
            type="button"
            className="text-sm font-semibold underline underline-offset-4"
            onClick={() => void loadDashboard(true)}
          >
            Try again
          </button>
        </section>
      ) : null}

      {loading ? (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="metric-card animate-pulse p-5"
            >
              <div className="h-3 w-28 rounded bg-slate-200" />
              <div className="mt-4 h-9 w-20 rounded bg-slate-200" />
              <div className="mt-3 h-3 w-36 rounded bg-slate-200" />
            </div>
          ))}
        </section>
      ) : usage ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {metricCards.map((metric) => (
              <div
                className="metric-card p-5"
                key={metric.label}
              >
                <p className="text-xs font-bold uppercase tracking-wide text-steel">
                  {metric.label}
                </p>

                <p className="mt-3 text-3xl font-bold text-ink">
                  {metric.value}
                </p>

                <p className="mt-1 text-sm text-steel">
                  {metric.detail}
                </p>
              </div>
            ))}
          </section>

          <section className="grid gap-6 xl:grid-cols-2">
            <article className="surface-card p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="page-kicker">Workflow capacity</p>
                  <h2 className="mt-2 text-xl font-semibold text-ink">
                    Workflow usage
                  </h2>
                </div>

                <span className="text-sm font-semibold text-ink">
                  {formatNumber(usage.workflows.total)} /{" "}
                  {formatLimit(usage.plan.workflow_limit)}
                </span>
              </div>

              {usage.plan.workflow_limit === -1 ? (
                <div className="mt-5 rounded-xl border border-pine/20 bg-mint px-4 py-3 text-sm text-pine">
                  Your plan includes unlimited workflows.
                </div>
              ) : (
                <>
                  <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-emerald-600 transition-all"
                      style={{ width: `${workflowUsagePercent}%` }}
                    />
                  </div>

                  <div className="mt-3 flex items-center justify-between text-sm text-steel">
                    <span>{workflowUsagePercent}% used</span>
                    <span>
                      {formatNumber(
                        usage.plan.remaining_workflows ?? 0,
                      )}{" "}
                      remaining
                    </span>
                  </div>
                </>
              )}

              <div className="mt-6 grid grid-cols-2 gap-3">
                <div className="surface-panel p-4">
                  <p className="text-xs font-semibold uppercase text-steel">
                    Active
                  </p>
                  <p className="mt-2 text-2xl font-bold text-ink">
                    {formatNumber(usage.workflows.active)}
                  </p>
                </div>

                <div className="surface-panel p-4">
                  <p className="text-xs font-semibold uppercase text-steel">
                    Inactive
                  </p>
                  <p className="mt-2 text-2xl font-bold text-ink">
                    {formatNumber(usage.workflows.inactive)}
                  </p>
                </div>
              </div>
            </article>

            <article className="surface-card p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="page-kicker">Monthly capacity</p>
                  <h2 className="mt-2 text-xl font-semibold text-ink">
                    Workflow runs
                  </h2>
                </div>

                <span className="text-sm font-semibold text-ink">
                  {formatNumber(usage.runs.total)} /{" "}
                  {formatLimit(usage.plan.monthly_run_limit)}
                </span>
              </div>

              {usage.plan.monthly_run_limit === -1 ? (
                <div className="mt-5 rounded-xl border border-pine/20 bg-mint px-4 py-3 text-sm text-pine">
                  Your plan includes unlimited workflow runs.
                </div>
              ) : (
                <>
                  <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-emerald-600 transition-all"
                      style={{ width: `${runUsagePercent}%` }}
                    />
                  </div>

                  <div className="mt-3 flex items-center justify-between text-sm text-steel">
                    <span>{runUsagePercent}% used</span>
                    <span>
                      {formatNumber(usage.plan.remaining_runs ?? 0)} remaining
                    </span>
                  </div>
                </>
              )}

              <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  ["Completed", usage.runs.completed],
                  ["Failed", usage.runs.failed],
                  ["Running", usage.runs.running],
                  ["Queued", usage.runs.queued],
                ].map(([label, value]) => (
                  <div
                    key={String(label)}
                    className="surface-panel p-4"
                  >
                    <p className="text-xs font-semibold uppercase text-steel">
                      {label}
                    </p>
                    <p className="mt-2 text-xl font-bold text-ink">
                      {formatNumber(Number(value))}
                    </p>
                  </div>
                ))}
              </div>
            </article>
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
            <article className="surface-card p-6">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="page-kicker">Activity</p>
                  <h2 className="mt-2 text-xl font-semibold text-ink">
                    Recent workflow runs
                  </h2>
                </div>

                <Link
                  href="/dashboard/workflows"
                  className="text-sm font-semibold text-pine hover:underline"
                >
                  View workflows
                </Link>
              </div>

              <div className="mt-5 grid gap-3">
                {usage.recent_runs.map((run) => (
                  <div
                    key={run.id}
                    className="rounded-xl border border-line bg-white p-4"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="font-semibold text-ink">
                          {run.workflow_name}
                        </p>

                        <p className="mt-1 text-xs text-steel">
                          {formatDateTime(run.created_at)}
                        </p>
                      </div>

                      <span className={statusClasses(run.status)}>
                        {displayStatus(run.status)}
                      </span>
                    </div>

                    {run.last_error ? (
                      <p className="mt-3 text-sm text-red-700">
                        {run.last_error}
                      </p>
                    ) : null}
                  </div>
                ))}

                     {usage.recent_runs.length === 0 ? (
  <div className="rounded-2xl border border-dashed border-line bg-slate-50/60 px-8 py-10 text-center">
    <h3 className="text-lg font-semibold text-ink">
      No workflow activity yet
    </h3>

    <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-steel">
      Your recent workflow executions will appear here after you create and run
      your first automation.
    </p>

    <Link
      href="/dashboard/workflows"
      className="btn-primary mt-6 inline-flex"
    >
      Create Workflow
    </Link>
  </div>
) : null}
              </div>
            </article>

            <article className="surface-card p-6">
              <div>
                <p className="page-kicker">Performance</p>
                <h2 className="mt-2 text-xl font-semibold text-ink">
                  Top workflows
                </h2>
                <p className="mt-2 text-sm text-steel">
                  Ranked by runs during {usage.period.label}.
                </p>
              </div>

              <div className="mt-5 grid gap-3">
                {usage.top_workflows.map((workflow, index) => (
                  <div
                    key={workflow.id}
                    className="flex items-center justify-between gap-4 rounded-xl border border-line bg-white p-4"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-linen text-sm font-bold text-pine">
                        {index + 1}
                      </div>

                      <div className="min-w-0">
                        <p className="truncate font-semibold text-ink">
                          {workflow.name}
                        </p>

                        <p className="mt-1 text-xs text-steel">
                          {workflow.is_active ? "Active" : "Inactive"}
                        </p>
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="font-bold text-ink">
                        {formatNumber(workflow.run_count)}
                      </p>
                      <p className="text-xs text-steel">runs</p>
                    </div>
                  </div>
                ))}

                {usage.top_workflows.length === 0 ? (
  <div className="rounded-2xl border border-dashed border-line bg-slate-50/60 px-8 py-10 text-center">
    <h3 className="text-lg font-semibold text-ink">
      No workflow statistics available
    </h3>

    <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-steel">
      Once your workflows start running, this section will automatically show
      your most active automations.
    </p>
  </div>
) : null}
              </div>
            </article>
          </section>

          <section className="grid gap-4 md:grid-cols-3">
            {[
              {
                title: "Build an automation",
                description:
                  "Create a workflow from scratch or start with a marketplace template.",
                href: "/dashboard/workflows",
                action: "Open workflow builder",
              },
              {
                title: "Connect your apps",
                description:
                  "Connect Gmail, Slack, and other services required by your workflows.",
                href: "/dashboard/integrations",
                action: "Manage integrations",
              },
              {
                title: "Increase capacity",
                description:
                  "Compare plans and upgrade when your automation volume grows.",
                href: "/dashboard/billing",
                action: "View plans",
              },
            ].map((item) => (
              <article
                className="surface-card premium-hover p-6 transition"
                key={item.title}
              >
                <h2 className="text-base font-bold text-ink">
                  {item.title}
                </h2>

                <p className="mt-2 text-sm leading-6 text-steel">
                  {item.description}
                </p>

                <Link
                  href={item.href}
                  className="mt-4 inline-block text-sm font-semibold text-pine hover:underline"
                >
                  {item.action}
                </Link>
              </article>
            ))}
          </section>
        </>
      ) : null}
    </div>
  );
}
