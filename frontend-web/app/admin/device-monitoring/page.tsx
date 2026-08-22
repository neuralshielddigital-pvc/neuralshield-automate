"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type DeviceItem = {
  user_email: string;
  device_name: string;
  os: string;
  status: string;
  last_seen: string;
  risk_level: string;
};

export default function DeviceMonitoringPage() {
  const [items, setItems] = useState<DeviceItem[]>([]);

  useEffect(() => {
    apiRequest<{ items: DeviceItem[] }>("/api/admin/device-monitoring")
      .then((res) => setItems(res.items || []));
  }, []);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              Employee Device Monitoring
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
                <th className="p-4">OS</th>
                <th className="p-4">Status</th>
                <th className="p-4">Risk</th>
                <th className="p-4">Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="p-4">{item.user_email}</td>
                  <td className="p-4">{item.device_name}</td>
                  <td className="p-4">{item.os}</td>
                  <td className="p-4">{item.status}</td>
                  <td className="p-4">{item.risk_level}</td>
                  <td className="p-4">
                    {new Date(item.last_seen).toLocaleString()}
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
