"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type ApiKey = {
id?: string;
user_email?: string;
key_name?: string;
status?: string;
created_at?: string;
};

export default function AdminApiKeysPage() {
const [items, setItems] = useState<ApiKey[]>([]);

async function load() {
const res = await apiRequest<{ items: ApiKey[] }>("/api/admin/api-keys");
setItems(res.items || []);
}

useEffect(() => {
load();
}, []);

async function revoke(id: string) {
await apiRequest(`/api/admin/api-keys/${id}/revoke`, { method: "POST" });
await load();
}

return ( <main className="dashboard-shell"> <section className="mx-auto max-w-7xl px-4 py-8"> <div className="mb-6 flex items-center justify-between"> <div> <p className="page-kicker">ADMIN</p> <h1 className="text-3xl font-semibold text-ink">API Keys Management</h1> </div> <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link> </div>


    <div className="surface-card p-6">
      <div className="table-wrap mt-4">
        <table className="w-full min-w-[1000px] text-left text-sm">
          <thead>
            <tr>
              <th className="p-3">User</th>
              <th className="p-3">Key Name</th>
              <th className="p-3">Status</th>
              <th className="p-3">Created</th>
              <th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="p-3" colSpan={5}>No API keys found.</td>
              </tr>
            ) : (
              items.map((k, idx) => (
                <tr key={k.id || idx}>
                  <td className="p-3">{k.user_email || "-"}</td>
                  <td className="p-3">{k.key_name || "-"}</td>
                  <td className="p-3">{k.status || "-"}</td>
                  <td className="p-3">
                    {k.created_at ? new Date(k.created_at).toLocaleDateString() : "-"}
                  </td>
                  <td className="p-3">
                    {k.id ? (
                      <button
                        className="btn-secondary px-3 py-1"
                        onClick={() => revoke(k.id!)}
                      >
                        Revoke
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  </section>
</main>


);
}
