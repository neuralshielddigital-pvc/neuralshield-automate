"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiRequest } from "@/lib/api";

type QueueStats = {
  queued: number;
  running: number;
  failed: number;
  completed: number;
  dead_letter: number;
  retry_queue: number;
  worker: {
    enabled: boolean;
    interval_seconds: number;
    status: string;
  };
};

export default function QueueDashboardPage() {
  const [stats, setStats] = useState<QueueStats | null>(null);

  useEffect(() => {
    async function load() {
      const data = await apiRequest(
        "/api/admin/queue-dashboard"
      ) as QueueStats;

      setStats(data);
    }

    load();
  }, []);

  if (!stats) {
    return (
      <main className="dashboard-shell p-8">
        Loading...
      </main>
    );
  }

  const cards = [
    ["Queued", stats.queued],
    ["Running", stats.running],
    ["Completed", stats.completed],
    ["Failed", stats.failed],
    ["Dead Letter", stats.dead_letter],
    ["Retry Queue", stats.retry_queue],
  ];

  return (
    <main className="dashboard-shell p-8">
      <div className="flex justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold">
            Queue Dashboard
          </h1>

          <p className="text-sm opacity-70 mt-2">
            Background worker and workflow queue monitoring.
          </p>
        </div>

        <Link href="/admin" className="btn-secondary">
          Back
        </Link>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mb-8">
        {cards.map(([title, value]) => (
          <div key={String(title)} className="card p-6">
            <p className="text-sm opacity-70">{title}</p>
            <h2 className="text-3xl font-bold mt-2">
              {value}
            </h2>
          </div>
        ))}
      </div>

      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">
          Worker
        </h2>

        <p>Status: {stats.worker.status}</p>
        <p>Enabled: {stats.worker.enabled ? "Yes" : "No"}</p>
        <p>Interval: {stats.worker.interval_seconds} seconds</p>
      </div>
    </main>
  );
}
