"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Commission = {
id: string;
affiliate_id?: string;
referral_code?: string;
amount?: string;
status?: string;
created_at?: string;
};

export default function AdminCommissionsPage() {
const [items, setItems] = useState<Commission[]>([]);

async function load() {
const res = await apiRequest<{ items: Commission[] }>("/api/admin/commissions");
setItems(res.items || []);
}

useEffect(() => {
load();
}, []);

async function action(id: string, actionName: "approve" | "reject" | "mark-paid") {
await apiRequest(`/api/admin/commissions/${id}/${actionName}`, { method: "POST" });
await load();
}

return ( <main className="dashboard-shell"> <section className="mx-auto max-w-7xl px-4 py-8"> <div className="mb-6 flex items-center justify-between"> <div> <p className="page-kicker">ADMIN</p> <h1 className="text-3xl font-semibold text-ink">Commission Management</h1> </div> <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link> </div>

```
    <div className="surface-card p-6">
      <div className="table-wrap mt-4">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead>
            <tr>
              <th className="p-3">Referral Code</th>
              <th className="p-3">Amount</th>
              <th className="p-3">Status</th>
              <th className="p-3">Created</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="p-3" colSpan={5}>No commissions found.</td>
              </tr>
            ) : (
              items.map((c) => (
                <tr key={c.id}>
                  <td className="p-3">{c.referral_code || "-"}</td>
                  <td className="p-3">INR {c.amount || "0"}</td>
                  <td className="p-3">{c.status || "-"}</td>
                  <td className="p-3">
                    {c.created_at ? new Date(c.created_at).toLocaleDateString() : "-"}
                  </td>
                  <td className="p-3 flex gap-2">
                    <button className="btn-secondary px-3 py-1" onClick={() => action(c.id, "approve")}>Approve</button>
                    <button className="btn-secondary px-3 py-1" onClick={() => action(c.id, "reject")}>Reject</button>
                    <button className="btn-primary px-3 py-1" onClick={() => action(c.id, "mark-paid")}>Mark Paid</button>
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
