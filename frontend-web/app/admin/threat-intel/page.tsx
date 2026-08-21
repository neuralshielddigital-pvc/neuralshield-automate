"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Threat = {
id?: string;
user_email?: string;
threat_type?: string;
severity?: string;
source?: string;
created_at?: string;
};

export default function AdminThreatIntelPage() {
const [items, setItems] = useState<Threat[]>([]);

async function load() {
const res = await apiRequest<{ items: Threat[] }>("/api/admin/threat-intel");
setItems(res.items || []);
}

useEffect(() => {
load();
}, []);

return ( <main className="dashboard-shell"> <section className="mx-auto max-w-7xl px-4 py-8"> <div className="mb-6 flex items-center justify-between"> <div> <p className="page-kicker">ADMIN</p> <h1 className="text-3xl font-semibold text-ink">Threat Intelligence</h1> </div> <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link> </div>


    <div className="surface-card p-6">
      <div className="table-wrap mt-4">
        <table className="w-full min-w-[1000px] text-left text-sm">
          <thead>
            <tr>
              <th className="p-3">User</th>
              <th className="p-3">Threat Type</th>
              <th className="p-3">Severity</th>
              <th className="p-3">Source</th>
              <th className="p-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="p-3" colSpan={5}>No threats found.</td>
              </tr>
            ) : (
              items.map((t, idx) => (
                <tr key={t.id || idx}>
                  <td className="p-3">{t.user_email || "-"}</td>
                  <td className="p-3">{t.threat_type || "-"}</td>
                  <td className="p-3">{t.severity || "-"}</td>
                  <td className="p-3">{t.source || "-"}</td>
                  <td className="p-3">
                    {t.created_at ? new Date(t.created_at).toLocaleDateString() : "-"}
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
