"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type DLPItem = {
  user_email: string;
  event_type: string;
  severity: string;
  status: string;
  details: string;
};

export default function DataLossPage() {
  const [items, setItems] = useState<DLPItem[]>([]);

  useEffect(() => {
    apiRequest<{ items: DLPItem[] }>("/api/admin/data-loss-prevention")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Data Loss Prevention
            </h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">
            Back
          </Link>
        </div>

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-linen/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">User</th>
                <th className="p-4">Event</th>
                <th className="p-4">Severity</th>
                <th className="p-4">Status</th>
                <th className="p-4">Details</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="p-4">{item.user_email}</td>
                  <td className="p-4">{item.event_type}</td>
                  <td className="p-4">{item.severity}</td>
                  <td className="p-4">{item.status}</td>
                  <td className="p-4">{item.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
