"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { cloneWorkflowTemplate } from "@/lib/workflows";
import { ApiError, apiRequest } from "@/lib/api";

type Template = {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  is_featured?: boolean;
  is_new?: boolean;
  install_count?: number;
  difficulty?: string;
  estimated_setup_minutes?: number;
  tags?: string[];
  definition: {
    trigger?: { type?: string };
    actions?: { type?: string }[];
  };
};

export default function DashboardTemplatesPage() {
  const router = useRouter();

  const [templates, setTemplates] = useState<Template[]>([]);
  const [category, setCategory] = useState("All");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<
  "featured" | "most_installed" | "newest" | "alphabetical"
>("featured");
  const [loading, setLoading] = useState(true);
  const [installingTemplateId, setInstallingTemplateId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<{ items: Template[] }>("/api/workflow-templates")
      .then((res) => setTemplates(res.items || []))
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Could not load templates.")
      )
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(
    () => ["All", "Featured", ...Array.from(new Set(templates.map((t) => t.category || "General")))],
    [templates]
  );

  const visibleTemplates = useMemo(() => {
    const q = search.trim().toLowerCase();

    return templates
      .filter((template) => {
        if (category === "Featured") return template.is_featured;
        if (category === "All") return true;
        return template.category === category;
      })
      .filter((template) => {
        if (!q) return true;

        const haystack = [
          template.name,
          template.description || "",
          template.category,
          template.difficulty || "",
          ...(template.tags || []),
          template.definition?.trigger?.type || "",
          ...(template.definition?.actions || []).map((a) => a.type || ""),
        ]
          .join(" ")
          .toLowerCase();

        return haystack.includes(q);
      })
            .sort((a, b) => {
        if (sortBy === "most_installed") {
          return (b.install_count || 0) - (a.install_count || 0);
        }

        if (sortBy === "newest") {
          return Number(b.is_new) - Number(a.is_new);
        }

        if (sortBy === "alphabetical") {
          return a.name.localeCompare(b.name);
        }

        if (Number(b.is_featured) !== Number(a.is_featured)) {
          return Number(b.is_featured) - Number(a.is_featured);
        }

        return (b.install_count || 0) - (a.install_count || 0);
      });
  }, [templates, category, search, sortBy]);

  const marketplaceStats = useMemo(() => {
    const categoryCount = new Set(
      templates.map((template) => template.category || "General")
    ).size;

    return {
      templates: templates.length,
      categories: categoryCount,
      featured: templates.filter((template) => template.is_featured).length,
      installs: templates.reduce(
        (total, template) => total + (template.install_count || 0),
        0
      ),
    };
  }, [templates]);

  const featuredTemplate = useMemo(() => {
    return (
      [...templates]
        .filter((template) => template.is_featured)
        .sort(
          (a, b) =>
            (b.install_count || 0) - (a.install_count || 0)
        )[0] ?? null
    );
  }, [templates]);

  async function handleInstallTemplate(templateId: string) {
    try {
      setInstallingTemplateId(templateId);

      const result = await cloneWorkflowTemplate(templateId);

      if (!result?.id) {
        throw new Error("Created workflow ID was not returned.");
      }

      if (result.already_installed) {
        alert("This template is already installed. Opening the existing workflow.");
      } else {
        setTemplates((current) =>
          current.map((template) =>
            template.id === templateId
              ? {
                  ...template,
                  install_count: (template.install_count || 0) + 1,
                }
              : template
          )
        );
      }

      const workflowId = encodeURIComponent(result.id);

      router.replace(
        `/dashboard/workflows?workflowId=${workflowId}&mode=edit&source=template`
      );
    } catch (error: unknown) {
      console.error("Template install failed:", error);

      let detail = "Template install failed. Please try again.";

      if (
        error &&
        typeof error === "object" &&
        "detail" in error &&
        typeof error.detail === "string"
      ) {
        detail = error.detail;
      } else if (error instanceof Error && error.message) {
        detail = error.message;
      }

      alert(detail);
    } finally {
      setInstallingTemplateId(null);
    }
  }

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="page-kicker">Automation Marketplace</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Workflow Templates
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">
              Install ready-made automations for AI sales workflows, Slack alerts,
              lead capture, email follow-ups, CRM workflows, and webhook operations.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              {
                label: "Templates",
                value: marketplaceStats.templates,
              },
              {
                label: "Categories",
                value: marketplaceStats.categories,
              },
              {
                label: "Featured",
                value: marketplaceStats.featured,
              },
              {
                label: "Total installs",
                value: marketplaceStats.installs,
              },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-2xl border border-line bg-white/70 px-4 py-3 text-center"
              >
                <p className="text-xl font-bold text-ink">
                  {item.value}
                </p>

                <p className="mt-1 text-xs font-medium text-steel">
                  {item.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {error ? <p className="alert-error">{error}</p> : null}

      <section className="surface-card grid gap-4 p-5">
        <input
          className="focus-ring w-full rounded-2xl px-4 py-3 text-sm"
          placeholder="Search templates by AI, sales, Slack, lead, webhook..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
  <p className="text-sm text-steel">
    Showing{" "}
    <span className="font-semibold text-ink">
      {visibleTemplates.length}
    </span>{" "}
    templates
  </p>

  <select
    className="focus-ring rounded-xl px-3 py-2 text-sm"
    value={sortBy}
    onChange={(event) =>
      setSortBy(
        event.target.value as
          | "featured"
          | "most_installed"
          | "newest"
          | "alphabetical"
      )
    }
  >
    <option value="featured">Featured first</option>
    <option value="most_installed">Most installed</option>
    <option value="newest">Newest</option>
    <option value="alphabetical">Alphabetical</option>
  </select>
</div>

        <div className="flex flex-wrap gap-2">
          {categories.map((item) => (
            <button
              key={item}
              className={item === category ? "btn-primary" : "btn-secondary"}
              onClick={() => setCategory(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </div>
      </section>

      {featuredTemplate ? (
        <section className="surface-card overflow-hidden border border-amber-200 bg-amber-50/60 p-6">
          <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <span className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">
                Featured template
              </span>

              <p className="mt-4 text-xs font-bold uppercase tracking-wide text-pine">
                {featuredTemplate.category || "General"}
              </p>

              <h2 className="mt-2 text-2xl font-bold text-ink">
                {featuredTemplate.name}
              </h2>

              <p className="mt-3 max-w-3xl text-sm leading-6 text-steel">
                {featuredTemplate.description ||
                  "Start quickly with this production-ready automation template."}
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-full border border-line bg-white px-3 py-1 text-xs font-semibold text-steel">
                  {featuredTemplate.difficulty || "Beginner"}
                </span>

                <span className="rounded-full border border-line bg-white px-3 py-1 text-xs font-semibold text-steel">
                  {featuredTemplate.estimated_setup_minutes || 5} min setup
                </span>

                <span className="rounded-full border border-line bg-white px-3 py-1 text-xs font-semibold text-steel">
                  {featuredTemplate.install_count || 0} installs
                </span>
              </div>
            </div>

            <button
              type="button"
              className="btn-primary min-w-40"
              disabled={installingTemplateId === featuredTemplate.id}
              onClick={() =>
                handleInstallTemplate(featuredTemplate.id)
              }
            >
              {installingTemplateId === featuredTemplate.id
                ? "Installing..."
                : "Install featured"}
            </button>
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {visibleTemplates.map((template) => {
          const trigger = template.definition?.trigger?.type || "-";
          const actions =
            template.definition?.actions?.map((a) => a.type).join(", ") || "-";
          const tags = template.tags || [];

          return (
            <article className="surface-card premium-hover flex flex-col p-6" key={template.id}>
              <div className="flex flex-wrap gap-2">
                {template.is_featured ? (
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">
                    ⭐ Featured
                  </span>
                ) : null}
                {template.is_new ? (
                  <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800">
                    New
                  </span>
                ) : null}
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
                  {template.difficulty || "Beginner"}
                </span>
              </div>

              <p className="mt-5 text-xs font-bold uppercase tracking-wide text-pine">
                {template.category || "General"}
              </p>

              <h2 className="mt-2 text-xl font-bold text-ink">
                {template.name}
              </h2>

              <p className="mt-3 min-h-16 text-sm leading-6 text-steel">
                {template.description || "Ready-to-use automation template."}
              </p>

              <div className="mt-5 grid gap-2 rounded-2xl border border-line bg-white/60 p-4 text-sm text-steel">
                <p>
                  <span className="font-semibold text-ink">Trigger:</span>{" "}
                  {trigger}
                </p>
                <p>
                  <span className="font-semibold text-ink">Actions:</span>{" "}
                  {actions}
                </p>
                <p>
                  <span className="font-semibold text-ink">Setup:</span>{" "}
                  {template.estimated_setup_minutes || 5} min
                </p>
                <p>
                  <span className="font-semibold text-ink">Installs:</span>{" "}
                  {template.install_count || 0}
                </p>
              </div>

              {tags.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {tags.slice(0, 5).map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-line px-3 py-1 text-xs font-medium text-steel"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}

              <button
                type="button"
                onClick={() => handleInstallTemplate(template.id)}
                disabled={installingTemplateId === template.id}
                className="btn-primary mt-6 w-full disabled:cursor-not-allowed disabled:opacity-60"
              >
                {installingTemplateId === template.id ? "Installing..." : "Install Template"}
              </button>
            </article>
          );
        })}

        {!loading && visibleTemplates.length === 0 ? (
          <div className="surface-card p-8 md:col-span-2 xl:col-span-3">
            <div className="mx-auto max-w-xl text-center">
              <p className="text-3xl" aria-hidden="true">
                🔎
              </p>

              <h2 className="mt-4 text-xl font-bold text-ink">
                No templates match your filters
              </h2>

              <p className="mt-2 text-sm leading-6 text-steel">
                Try a different search, clear the selected category, or
                browse featured templates.
              </p>

              <div className="mt-5 flex flex-wrap justify-center gap-3">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setSearch("");
                    setCategory("All");
                    setSortBy("featured");
                  }}
                >
                  Clear filters
                </button>

                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    setSearch("");
                    setCategory("Featured");
                    setSortBy("featured");
                  }}
                >
                  Browse featured
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </section>

      <section className="surface-card rounded-3xl border border-pine/20 bg-mint/30 p-8">
  <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
    <div>
      <h2 className="text-2xl font-bold text-ink">
        Need a custom automation?
      </h2>

      <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
        Build your own workflow from scratch or customize an installed template
        to match your business process.
      </p>
    </div>

    <div className="flex flex-wrap gap-3">
      <Link
        href="/dashboard/workflows"
        className="btn-primary"
      >
        Create Workflow
      </Link>

      <Link
        href="/dashboard/workflows"
        className="btn-secondary"
      >
        View Workflows
      </Link>
    </div>
  </div>
</section>
    </div>
  );
}
