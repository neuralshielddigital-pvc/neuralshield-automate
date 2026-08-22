"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";
import { clearTokens } from "@/lib/token-storage";

type AdminUser = {
  user_id?: string;
  id?: string;
  email: string;
  role?: string;
  tenant_name?: string;
  tenant_id?: string;
  is_active?: boolean;
  created_at?: string;
};

type UsersResponse = {
  items?: AdminUser[];
  pagination?: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
};

function formatDate(value?: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function AdminUsersPage() {
  const router = useRouter();
  const [data, setData] = useState<UsersResponse | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function updateUserRole(userId: string, role: string) {
    try {
      await apiRequest(`/api/admin/users/${userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      loadUsers(search);
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Could not update user role.");
    }
  }

  async function updateUserStatus(userId: string, isActive: boolean) {
    try {
      await apiRequest(`/api/admin/users/${userId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: isActive }),
      });
      loadUsers(search);
    } catch (err) {
      alert(err instanceof ApiError ? err.detail : "Could not update user status.");
    }
  }

  function loadUsers(query = "") {
    setLoading(true);
    setError("");

    const qs = new URLSearchParams();
    if (query.trim()) qs.set("search", query.trim());

    apiRequest<UsersResponse>(`/api/admin/users${qs.toString() ? `?${qs.toString()}` : ""}`)
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearTokens();
          router.replace("/login");
          return;
        }
        setError(err instanceof ApiError ? err.detail : "Could not load users.");
      })
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadUsers();
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Users</h1>
            <p className="text-steel">Manage SaaS users, roles, tenant access, and account status.</p>
          </div>
          <div className="flex gap-3">
            <Link href="/admin/users/create" className="btn-primary px-4 py-2">Create User</Link>
            <div className="flex gap-3">

  <Link href="/admin" className="btn-secondary px-4 py-2">
    Back
  </Link>
</div>
          </div>
        </div>

        <section className="surface-card mb-6 p-4">
          <form
            className="flex gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              loadUsers(search);
            }}
          >
            <input
              className="w-full rounded-2xl border border-line bg-white px-4 py-3"
              placeholder="Search user email..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <button className="btn-primary px-5 py-3" type="submit">Search</button>
          </form>
        </section>

        {error ? <p className="alert-error mb-6">{error}</p> : null}
        {loading ? <p>Loading users...</p> : null}

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">Email</th>
                <th className="p-4">Role</th>
                <th className="p-4">Tenant</th>
                <th className="p-4">Status</th>
                <th className="p-4">Created</th>
                <th className="p-4">Action</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).length ? data!.items!.map((user, index) => (
                <tr key={user.user_id ?? user.id ?? index} className="border-t border-line">
                  <td className="p-4 font-medium">{user.email}</td>
                  <td className="p-4">
                    <select
                      className="rounded-xl border border-line bg-white px-3 py-2"
                      value={user.role ?? "USER"}
                      onChange={(e) => updateUserRole(String(user.user_id ?? user.id), e.target.value)}
                    >
                      <option value="USER">USER</option>
                      <option value="ADMIN">ADMIN</option>
                      <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                    </select>
                  </td>
                  <td className="p-4">{user.tenant_name ?? user.tenant_id ?? "-"}</td>
                  <td className="p-4">{user.is_active ? "Active" : "Disabled"}</td>
                  <td className="p-4">{formatDate(user.created_at)}</td>
                  <td className="p-4">
                    <button
                      className="btn-secondary px-3 py-2"
                      onClick={() => updateUserStatus(String(user.user_id ?? user.id), !user.is_active)}
                    >
                      {user.is_active ? "Disable" : "Enable"}
                    </button>
                  </td>
                  <td className="p-4">
                    <Link href={`/admin/users/${user.user_id ?? user.id}`} className="btn-secondary px-3 py-2">
                      View
                    </Link>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td className="p-4" colSpan={6}>No users found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
