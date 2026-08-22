"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type PolicyViolation = {
  user_email: string;
  violation_type: string;
  severity: string;
  status: string;
  details: string;
  created_at: string;
};

export default function PolicyViolationsPage() {
  const [items, setItems] = useState<PolicyViolation[]>([]);

  useEffect(() => {
    apiRequest<{ items: PolicyViolation[] }>("/api/admin/policy-violations")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Policy Violations
            </h1>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">
            Back
          </Link>
        </div>

        <section className="surface-card overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-line/80 text-xs uppercase text-steel">
              <tr>
                <th className="p-4">User</th>
                <th className="p-4">Violation</th>
                <th className="p-4">Severity</th>
                <th className="p-4">Status</th>
                <th className="p-4">Details</th>
                <th className="p-4">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? (
                items.map((v, i) => (
                  <tr key={i} className="border-b border-line">
                    <td className="p-4">{v.user_email}</td>
                    <td className="p-4">{v.violation_type}</td>
                    <td className="p-4">{v.severity}</td>
                    <td className="p-4">{v.status}</td>
                    <td className="p-4">{v.details}</td>
                    <td className="p-4">
                      {new Date(v.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="p-4" colSpan={6}>
                    No policy violations found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </main>
  );
}
