"use client";

import { useState } from "react";

export default function EmbedPage() {
  const [tenantSlug, setTenantSlug] = useState("neuralshielddigital");
  const [copied, setCopied] = useState(false);

  const publicFormUrl = `https://app.neuralshielddigital.com/lead-form`;

  const embedCode = `<form method="POST" action="https://api.neuralshielddigital.com/api/public/leads">
  <input type="hidden" name="tenant_slug" value="${tenantSlug}" />
  <input name="name" placeholder="Name" />
  <input name="email" type="email" placeholder="Email" required />
  <input name="phone" placeholder="Phone" />
  <textarea name="message" placeholder="Message"></textarea>
  <input type="hidden" name="source" value="website_embed" />
  <button type="submit">Submit</button>
</form>`;

  async function copyCode() {
    await navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function copyFormUrl() {
    await navigator.clipboard.writeText(publicFormUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6">
        <h1 className="text-3xl font-semibold text-ink">Embed Lead Form</h1>
        <p className="mt-2 text-sm text-steel">
          Capture leads from any website. Every submitted lead is saved in your CRM
          and automatically triggers workflows using the NEW_LEAD trigger.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="surface-card p-6 grid gap-4">
          <h2 className="text-lg font-semibold text-ink">Public Lead Form</h2>
          <p className="text-sm text-steel">
            Share this hosted form link directly with prospects.
          </p>

          <div className="surface-panel break-all p-4 text-sm text-steel">
            {publicFormUrl}
          </div>

          <button className="btn-primary w-fit" onClick={copyFormUrl} type="button">
            {copied ? "Copied" : "Copy Form Link"}
          </button>
        </div>

        <div className="surface-card p-6 grid gap-4">
          <h2 className="text-lg font-semibold text-ink">Tenant Slug</h2>
          <p className="text-sm text-steel">
            This identifies your workspace for public lead submissions.
          </p>

          <input
            className="focus-ring px-3.5 py-2.5 text-sm"
            value={tenantSlug}
            onChange={(event) => setTenantSlug(event.target.value)}
            placeholder="tenant slug"
          />
        </div>
      </section>

      <section className="surface-card p-6 grid gap-4">
        <h2 className="text-lg font-semibold text-ink">Website Embed Code</h2>
        <p className="text-sm text-steel">
          Paste this HTML into your landing page, website, or no-code builder.
        </p>

        <textarea
          className="focus-ring min-h-[300px] px-3.5 py-2.5 text-sm"
          value={embedCode}
          readOnly
        />

        <button className="btn-primary w-fit" onClick={copyCode} type="button">
          {copied ? "Copied" : "Copy Embed Code"}
        </button>
      </section>
    </div>
  );
}
