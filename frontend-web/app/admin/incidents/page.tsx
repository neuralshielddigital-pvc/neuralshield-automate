"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Incident = {
id?: string;
user_email?: string;
incident_type?: string;
severity?: string;
status?: string;
risk_score?: number;
created_at?: string;
};

export default function AdminIncidentsPage() {
const [items, setItems] = useState<Incident[]>([]);

async function load() {
const res = await apiRequest<{ items: Incident[] }>("/api/admin/incidents");
setItems(res.items || []);
}

useEffect(() => {
load();
}, []);

return ( <main className="dashboard-shell"> <section className="mx-auto max-w-7xl px-4 py-8"> <div className="mb-6 flex items-center justify-between"> <div> <p className="page-kicker">ADMIN</p> <h1 className="text-3xl font-semibold text-ink">Security Incidents</h1> </div> <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link> </div>

```
    <div className="surface-card p-6">
      <div className="table-wrap mt-4">
        <table className="w-full min-w-[1000px] text-left text-sm">
          <thead>
            <tr>
              <th className="p-3">User</th>
              <th className="p-3">Incident Type</th>
              <th className="p-3">Severity</th>
              <th className="p-3">Status</th>
              <th className="p-3">Risk Score</th>
              <th className="p-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="p-3" colSpan={6}>No incidents found.</td>
              </tr>
            ) : (
              items.map((i, idx) => (
                <tr key={i.id || idx}>
                  <td className="p-3">{i.user_email || "-"}</td>
                  <td className="p-3">{i.incident_type || "-"}</td>
                  <td className="p-3">{i.severity || "-"}</td>
                  <td className="p-3">{i.status || "-"}</td>
                  <td className="p-3">{i.risk_score ?? "-"}</td>
                  <td className="p-3">
                    {i.created_at ? new Date(i.created_at).toLocaleDateString() : "-"}
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
