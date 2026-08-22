"use client";

import Link from "next/link";

export default function AdminSettingsPage() {
  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Platform Settings</h1>
            <p className="mt-2 text-sm text-steel">Company, billing, security, and environment configuration.</p>
          </div>
          <Link href="/admin" className="btn-secondary px-4 py-2">Back</Link>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Company", "NeuralShieldDigital"],
            ["Support Email", "neuralshielddigital@gmail.com"],
            ["Currency", "USD"],
            ["Payment Provider", "Paddle"],
          ].map(([label, value]) => (
            <div className="metric-card" key={label}>
              <p className="text-xs font-semibold uppercase text-steel">{label}</p>
              <p className="mt-3 text-xl font-semibold text-ink">{value}</p>
            </div>
          ))}
        </div>

        <section className="surface-card mt-6 p-6">
          <h2 className="text-xl font-semibold text-ink">System Configuration</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div>
              <p className="text-xs uppercase text-steel">Backend</p>
              <p>FastAPI + systemd</p>
            </div>
            <div>
              <p className="text-xs uppercase text-steel">Frontend</p>
              <p>Next.js + PM2</p>
            </div>
            <div>
              <p className="text-xs uppercase text-steel">Database</p>
              <p>Neon PostgreSQL</p>
            </div>
            <div>
              <p className="text-xs uppercase text-steel">Reverse Proxy</p>
              <p>Nginx</p>
            </div>
            <div>
              <p className="text-xs uppercase text-steel">Security</p>
              <p>JWT, RBAC, UFW, Fail2ban</p>
            </div>
            <div>
              <p className="text-xs uppercase text-steel">Maintenance Mode</p>
              <p>Disabled</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
