"use client";

import { FormEvent, useState } from "react";
import { ApiError } from "@/lib/api";
import { submitPublicLead } from "@/lib/public-leads";

const blankForm = {
  name: "",
  email: "",
  phone: "",
  message: ""
};

export default function LeadFormPage() {
  const [form, setForm] = useState(blankForm);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setSuccess("");
    setError("");
    try {
      const response = await submitPublicLead({
        tenant_slug: "neuralshielddigital",
        name: form.name || null,
        email: form.email,
        phone: form.phone || null,
        source: "website",
        message: form.message || null
      });
      setSuccess(response.message);
      setForm(blankForm);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not submit your request.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="lead-form-shell">
      <section className="mx-auto grid min-h-screen max-w-6xl items-center gap-10 px-4 py-10 lg:grid-cols-[1fr_460px]">
        <div>
          <div className="brand-mark h-12 w-12 text-sm ring-4 ring-mint/70">
            NS
          </div>
          <p className="page-kicker mt-8">NeuralShieldDigital</p>
          <h1 className="mt-3 max-w-2xl text-4xl font-semibold leading-tight text-ink md:text-5xl">
            Build smarter marketing automation around every new lead.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-steel">
            Tell us what you need automated. Our team will review your request and follow up with the right next step.
          </p>
          <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-3">
            {["Automation strategy", "CRM pipeline", "Workflow setup"].map((item) => (
              <div className="rounded-xl border border-line bg-white/85 p-4 text-sm font-semibold text-ink shadow-sm" key={item}>
                {item}
              </div>
            ))}
          </div>
        </div>

        <form className="surface-card p-6 sm:p-8" onSubmit={handleSubmit}>
          <h2 className="text-2xl font-semibold text-ink">Request a callback</h2>
          <p className="mt-2 text-sm leading-6 text-steel">Share your details and a short note about the automation you want to build.</p>
          <div className="mt-5 grid gap-4">
            <input
              className="focus-ring px-3.5 py-3 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              placeholder="Name"
              value={form.name}
            />
            <input
              className="focus-ring px-3.5 py-3 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              placeholder="Email"
              required
              type="email"
              value={form.email}
            />
            <input
              className="focus-ring px-3.5 py-3 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
              placeholder="Phone"
              value={form.phone}
            />
            <textarea
              className="focus-ring min-h-32 px-3.5 py-3 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))}
              placeholder="Message"
              value={form.message}
            />
          </div>
          {success ? <p className="alert-success mt-4">{success}</p> : null}
          {error ? <p className="alert-error mt-4">{error}</p> : null}
          <button className="btn-primary mt-5 w-full py-3" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit request"}
          </button>
        </form>
      </section>
    </main>
  );
}
