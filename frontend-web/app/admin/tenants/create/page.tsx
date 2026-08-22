"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";

export default function CreateTenantPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", slug: "" });

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    try {
      await apiRequest("/api/admin/tenants/create", {
        method: "POST",
        body: JSON.stringify(form),
      });
      router.push("/admin/tenants");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to create tenant.");
    }
  }

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Create Tenant</h1>
          </div>
          <Link href="/admin/tenants" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <form onSubmit={submit} className="surface-card grid gap-4 p-6">
          {error ? <p className="alert-error">{error}</p> : null}

          <input className="rounded-2xl border border-line px-4 py-3" placeholder="Tenant name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="rounded-2xl border border-line px-4 py-3" placeholder="Slug e.g. client-company" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })} />

          <button className="btn-primary px-5 py-3" type="submit">Create Tenant</button>
        </form>
      </div>
    </main>
  );
}
