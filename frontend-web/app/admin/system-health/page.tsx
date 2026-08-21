"use client";

import Link from "next/link";

export default function SystemHealthPage() {
  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">

        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">
              System Health
            </h1>
            <p className="text-steel">
              Infrastructure, monitoring and security overview.
            </p>
          </div>

          <Link
            href="/admin"
            className="btn-secondary px-4 py-2"
          >
            Back
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-4">

          <div className="surface-card p-5">
            <p className="text-xs uppercase text-steel">Backend</p>
            <p className="mt-2 text-2xl font-semibold">ONLINE</p>
          </div>

          <div className="surface-card p-5">
            <p className="text-xs uppercase text-steel">Database</p>
            <p className="mt-2 text-2xl font-semibold">ONLINE</p>
          </div>

          <div className="surface-card p-5">
            <p className="text-xs uppercase text-steel">API</p>
            <p className="mt-2 text-2xl font-semibold">HEALTHY</p>
          </div>

          <div className="surface-card p-5">
            <p className="text-xs uppercase text-steel">Security</p>
            <p className="mt-2 text-2xl font-semibold">OK</p>
          </div>

        </div>

        <section className="surface-card mt-6 p-6">
          <h2 className="text-xl font-semibold">Infrastructure</h2>

          <div className="mt-4 grid gap-4 md:grid-cols-3">

            <div>
              <p className="text-xs uppercase text-steel">Server</p>
              <p>AWS EC2</p>
            </div>

            <div>
              <p className="text-xs uppercase text-steel">Database</p>
              <p>Neon PostgreSQL</p>
            </div>

            <div>
              <p className="text-xs uppercase text-steel">Frontend</p>
              <p>Next.js + PM2</p>
            </div>

            <div>
              <p className="text-xs uppercase text-steel">Backend</p>
              <p>FastAPI + systemd</p>
            </div>

            <div>
              <p className="text-xs uppercase text-steel">Reverse Proxy</p>
              <p>Nginx</p>
            </div>

            <div>
              <p className="text-xs uppercase text-steel">Firewall</p>
              <p>UFW Enabled</p>
            </div>

          </div>
        </section>

      </div>
    </main>
  );
}
