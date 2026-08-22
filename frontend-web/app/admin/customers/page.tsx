"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Customer = {
  id: string;
  email: string;
  role: string;
  tenant_name: string;
  is_active: boolean;
  created_at: string;
};

export default function AdminCustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);

  useEffect(() => {
    async function load() {
      const res = await apiRequest<{ items: Customer[] }>("/api/admin/users");
      setCustomers(res.items || []);
    }
    load();
  }, []);

  return (
    <main className="dashboard-shell">
      <header className="dashboard-topbar">
        <div>
          <p className="text-sm font-semibold text-ink">NeuralShieldDigital Admin</p>
          <p className="text-xs text-steel">Customers</p>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-8">
        <div className="surface-card p-6">
          <h1 className="text-3xl font-semibold text-ink">Customers</h1>

          <div className="table-wrap mt-6">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Tenant</th>
                  <th>Active</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {customers.map((c) => (
                  <tr key={c.id}>
                    <td>{c.email}</td>
                    <td>{c.role}</td>
                    <td>{c.tenant_name}</td>
                    <td>{c.is_active ? "Yes" : "No"}</td>
                    <td>{new Date(c.created_at).toLocaleDateString()}</td>
                    <td className="flex gap-2 py-3">
                      <Link href={`/admin/customers/${c.id}`} className="btn-primary px-3 py-1">
                        View
                      </Link>

                      <Link href={`/admin/customers/${c.id}/billing`} className="btn-secondary px-3 py-1">
                        Billing
                      </Link>

                      <button
  className="btn-secondary px-3 py-1"
  onClick={async () => {
    if (
      !confirm(
        `${c.is_active ? "Suspend" : "Reactivate"} ${c.email}?`
      )
    )
      return;

    const endpoint = c.is_active
      ? `/api/admin/users/${c.id}/suspend`
      : `/api/admin/users/${c.id}/reactivate`;

    await apiRequest(endpoint, { method: "PATCH" });

    setCustomers((items) =>
      items.map((item) =>
        item.id === c.id
          ? { ...item, is_active: !item.is_active }
          : item
      )
    );
  }}
>
  {c.is_active ? "Suspend" : "Reactivate"}
</button>







                      <button
  className="btn-secondary px-3 py-1 text-red-600"
  onClick={async () => {
    if (!confirm(`Delete ${c.email}?`)) return;

    await apiRequest(`/api/admin/users/${c.id}`, {
      method: "DELETE",
    });

    setCustomers((items) =>
      items.filter((item) => item.id !== c.id)
    );
  }}
>
  Delete
</button>


                    </td>
                  </tr>
                ))}
              </tbody>

            </table>
          </div>
        </div>
      </section>
    </main>
  );
}
