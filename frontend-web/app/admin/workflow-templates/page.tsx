"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";

type Template = {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  is_active: boolean;
  definition: {
    trigger?: {
      type?: string;
      config?: Record<string, unknown>;
    };
    actions?: {
      type: string;
      config?: Record<string, unknown>;
    }[];
  };
};

type ClonedWorkflow = {
  id: string;
  name: string;
};

export default function WorkflowTemplatesPage() {
  const router = useRouter();

  const [templates, setTemplates] = useState<Template[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [cloningId, setCloningId] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<{ items: Template[] }>("/api/workflow-templates")
      .then((response) => {
        setTemplates(response.items ?? []);
      })
      .catch((err: unknown) => {
        setError(
          err instanceof ApiError
            ? err.detail
            : "Failed to load templates."
        );
      });
  }, []);

  const groupedTemplates = useMemo(() => {
    return templates.reduce<Record<string, Template[]>>(
      (groups, template) => {
        const category = template.category || "General";

        if (!groups[category]) {
          groups[category] = [];
        }

        groups[category].push(template);

        return groups;
      },
      {}
    );
  }, [templates]);

  async function cloneTemplate(templateId: string) {
    if (cloningId) {
      return;
    }

    setError("");
    setMessage("");
    setCloningId(templateId);

    try {
      const workflow = await apiRequest<ClonedWorkflow>(
        `/api/workflow-templates/${templateId}/clone`,
        {
          method: "POST",
        }
      );

      if (!workflow?.id) {
        throw new Error("Created workflow ID was not returned.");
      }

      setMessage(`Workflow created: ${workflow.name}`);

      const workflowId = encodeURIComponent(workflow.id);

      router.push(
        `/dashboard/workflows?workflowId=${workflowId}&mode=edit&source=template`
      );
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Failed to use template."
      );
    } finally {
      setCloningId(null);
    }
  }

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="page-kicker">ADMIN</p>

            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Workflow Templates
            </h1>

            <p className="mt-2 text-sm text-steel">
              Ready-made automations customers can clone in one click.
            </p>
          </div>

          <Link href="/admin" className="btn-secondary px-4 py-2">
            Back
          </Link>
        </div>

        {error ? (
          <p className="alert-error mb-4">{error}</p>
        ) : null}

        {message ? (
          <p className="alert-success mb-4">{message}</p>
        ) : null}

        <div className="grid gap-6">
          {Object.keys(groupedTemplates).length ? (
            Object.entries(groupedTemplates).map(([category, items]) => (
              <section key={category} className="surface-card p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-ink">
                    {category}
                  </h2>

                  <span className="text-xs text-steel">
                    {items.length} templates
                  </span>
                </div>

                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {items.map((template) => {
                    const isCloning = cloningId === template.id;
                    const isAnyTemplateCloning = cloningId !== null;

                    return (
                      <article
                        key={template.id}
                        className="rounded-2xl border border-line p-5"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h3 className="text-lg font-semibold text-ink">
                              {template.name}
                            </h3>

                            <p className="mt-2 text-sm text-steel">
                              {template.description ??
                                "No description available."}
                            </p>
                          </div>

                          <span className="rounded-full bg-linen px-3 py-1 text-xs text-steel">
                            {template.is_active ? "Active" : "Inactive"}
                          </span>
                        </div>

                        <div className="mt-4 text-xs text-steel">
                          <p>
                            Trigger:{" "}
                            {template.definition?.trigger?.type ?? "N/A"}
                          </p>

                          <p>
                            Actions:{" "}
                            {(template.definition?.actions ?? [])
                              .map((action) => action.type)
                              .join(" → ") || "N/A"}
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={() => cloneTemplate(template.id)}
                          disabled={isAnyTemplateCloning}
                          className="btn-primary mt-5 w-full px-4 py-2 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {isCloning
                            ? "Creating workflow..."
                            : "Use Template"}
                        </button>
                      </article>
                    );
                  })}
                </div>
              </section>
            ))
          ) : (
            <section className="surface-card p-6 text-sm text-steel">
              No workflow templates found.
            </section>
          )}
        </div>
      </div>
    </main>
  );
}
