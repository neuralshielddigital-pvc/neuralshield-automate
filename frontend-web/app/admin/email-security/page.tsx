"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type EmailThreat = {
  user_email: string;
  threat_type: string;
  sender: string;
  status: string;
  risk_level: string;
  created_at: string;
};

export default function EmailSecurityPage() {
  const [items, setItems] = useState<EmailThreat[]>([]);

  useEffect(() => {
    apiRequest<{ items: EmailThreat[] }>("/api/admin/email-security")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Email Security Monitoring
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
                <th className="p-4">Threat</th>
                <th className="p-4">Sender</th>
                <th className="p-4">Status</th>
                <th className="p-4">Risk</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="p-4">{e.user_email}</td>
                  <td className="p-4">{e.threat_type}</td>
                  <td className="p-4">{e.sender}</td>
                  <td className="p-4">{e.status}</td>
                  <td className="p-4">{e.risk_level}</td>
                  <td className="p-4">
                    {new Date(e.created_at).toLocaleString()}
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
