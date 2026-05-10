export default function DashboardPage() {
  return (
    <div className="grid gap-7">
      <section className="surface-card overflow-hidden p-6 sm:p-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_320px] lg:items-end">
          <div>
            <p className="page-kicker">Workspace</p>
            <h1 className="mt-2 text-3xl font-bold text-ink sm:text-4xl">Dashboard</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-steel">
              Your NeuralShieldDigital workspace brings billing, affiliate tracking, lead capture, and workflow automation into one operating dashboard.
            </p>
          </div>
          <div className="surface-panel p-4">
            <p className="text-xs font-bold uppercase text-pine">Operating status</p>
            <p className="mt-2 text-2xl font-bold text-ink">Live workspace</p>
            <p className="mt-1 text-sm text-steel">Automation, CRM, billing, and partner modules are available.</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Active modules", "6", "Billing, CRM, workflows"],
          ["Lead pipeline", "5", "Kanban stages"],
          ["Workflow actions", "4", "Email, webhook, CRM, audit"],
          ["Admin views", "8", "Platform tables"]
        ].map(([label, value, detail]) => (
          <div className="metric-card p-5" key={label}>
            <p className="text-xs font-bold uppercase text-steel">{label}</p>
            <p className="mt-3 text-3xl font-bold text-ink">{value}</p>
            <p className="mt-1 text-sm text-steel">{detail}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["Billing", "Manage subscription, plan status, and Stripe checkout."],
          ["Lead CRM", "Capture, qualify, and organize every inbound lead."],
          ["Automation", "Trigger workflows from webhooks, campaigns, and CRM events."]
        ].map(([title, description]) => (
          <div className="surface-card premium-hover p-6 transition" key={title}>
            <h2 className="text-base font-bold text-ink">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-steel">{description}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
