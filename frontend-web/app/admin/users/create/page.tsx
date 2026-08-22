"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";
import { getAccessToken } from "@/lib/token-storage";

export default function CreateUserPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    email: "",
    password: "",
    role: "USER",
    tenant_id: "",
  });

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    try {
      const token = getAccessToken();

      await apiRequest("/api/admin/users/create", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: JSON.stringify(form),
      });

      router.push("/admin/users");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to create user.");
    }
  }

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-2xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Create User</h1>
          </div>
          <Link href="/admin/users" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <form onSubmit={submit} className="surface-card grid gap-4 p-6">
          {error ? <p className="alert-error">{error}</p> : null}

          <input className="rounded-2xl border border-line px-4 py-3" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input className="rounded-2xl border border-line px-4 py-3" placeholder="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />

          <select className="rounded-2xl border border-line px-4 py-3" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="USER">USER</option>
            <option value="ADMIN">ADMIN</option>
            <option value="SUPER_ADMIN">SUPER_ADMIN</option>
          </select>

          <input className="rounded-2xl border border-line px-4 py-3" placeholder="Tenant ID" value={form.tenant_id} onChange={(e) => setForm({ ...form, tenant_id: e.target.value })} />

          <button className="btn-primary px-5 py-3" type="submit">Create User</button>
        </form>
      </div>
    </main>
  );
}
