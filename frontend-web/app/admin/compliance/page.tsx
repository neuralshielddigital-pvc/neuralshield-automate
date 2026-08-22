"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type ComplianceItem = {
  framework: string;
  status: string;
  score: number;
  last_check: string;
};

export default function CompliancePage() {
  const [items, setItems] = useState<ComplianceItem[]>([]);

  useEffect(() => {
    apiRequest<{ items: ComplianceItem[] }>("/api/admin/compliance")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Compliance Center
            </h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">
            Back
          </Link>
        </div>

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th className="p-4">Framework</th>
                <th className="p-4">Status</th>
                <th className="p-4">Score</th>
                <th className="p-4">Last Check</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c, i) => (
                <tr key={i}>
                  <td className="p-4">{c.framework}</td>
                  <td className="p-4">{c.status}</td>
                  <td className="p-4">{c.score}%</td>
                  <td className="p-4">
                    {new Date(c.last_check).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
