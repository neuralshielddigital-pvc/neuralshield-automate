"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type Endpoint = {
  user_email: string;
  device_name: string;
  antivirus_status: string;
  malware_detected: string;
  risk_level: string;
  last_scan: string;
};

export default function EndpointSecurityPage() {
  const [items, setItems] = useState<Endpoint[]>([]);

  useEffect(() => {
    apiRequest<{ items: Endpoint[] }>("/api/admin/endpoint-security")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Endpoint Security Monitoring
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
                <th className="p-4">Device</th>
                <th className="p-4">Antivirus</th>
                <th className="p-4">Malware</th>
                <th className="p-4">Risk</th>
                <th className="p-4">Last Scan</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="p-4">{e.user_email}</td>
                  <td className="p-4">{e.device_name}</td>
                  <td className="p-4">{e.antivirus_status}</td>
                  <td className="p-4">{e.malware_detected}</td>
                  <td className="p-4">{e.risk_level}</td>
                  <td className="p-4">
                    {new Date(e.last_scan).toLocaleString()}
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
