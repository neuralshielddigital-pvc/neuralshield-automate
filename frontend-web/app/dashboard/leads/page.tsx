"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import { createLead, deleteLead, getLeads, updateLeadNotes, updateLeadStage } from "@/lib/leads";
import type { Lead, LeadStage } from "@/lib/types";

const blankForm = {
  name: "",
  email: "",
  phone: "",
  source: "",
  tags: ""
};

const stages: Array<{ value: LeadStage; label: string }> = [
  { value: "NEW", label: "New" },
  { value: "CONTACTED", label: "Contacted" },
  { value: "QUALIFIED", label: "Qualified" },
  { value: "WON", label: "Won" },
  { value: "LOST", label: "Lost" }
];

const publicFormUrl = "http://localhost:3000/lead-form";

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [form, setForm] = useState(blankForm);
  const [search, setSearch] = useState("");
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [notesDraft, setNotesDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const selectedLead = useMemo(
    () => leads.find((lead) => lead.id === selectedLeadId) ?? leads[0] ?? null,
    [leads, selectedLeadId]
  );

  async function loadLeads(nextSearch = search) {
    const response = await getLeads(nextSearch);
    setLeads(response.items);
    if (!selectedLeadId || !response.items.some((lead) => lead.id === selectedLeadId)) {
      setSelectedLeadId(response.items[0]?.id ?? null);
      setNotesDraft(response.items[0]?.notes ?? "");
    }
  }

  useEffect(() => {
    loadLeads()
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Could not load leads."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setNotesDraft(selectedLead?.notes ?? "");
  }, [selectedLead?.id]);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await loadLeads(search);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed.");
    }
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const lead = await createLead({
        name: form.name || null,
        email: form.email,
        phone: form.phone || null,
        source: form.source || null,
        tags: form.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
        metadata: {}
      });
      setForm(blankForm);
      setSelectedLeadId(lead.id);
      setMessage("Lead added.");
      await loadLeads();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not add lead.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(leadId: string) {
    setError("");
    setMessage("");
    try {
      await deleteLead(leadId);
      setMessage("Lead deleted.");
      await loadLeads();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete lead.");
    }
  }

  async function moveLead(leadId: string, stage: LeadStage) {
    setError("");
    setMessage("");
    try {
      const updated = await updateLeadStage(leadId, stage);
      setLeads((current) => current.map((lead) => (lead.id === leadId ? updated : lead)));
      setSelectedLeadId(updated.id);
      setMessage("Lead stage updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update stage.");
    }
  }

  async function saveNotes() {
    if (!selectedLead) {
      return;
    }
    setError("");
    setMessage("");
    try {
      const updated = await updateLeadNotes(selectedLead.id, notesDraft, new Date().toISOString());
      setLeads((current) => current.map((lead) => (lead.id === selectedLead.id ? updated : lead)));
      setMessage("Notes saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save notes.");
    }
  }

  async function copyPublicFormUrl() {
    await navigator.clipboard.writeText(publicFormUrl);
    setMessage("Public form URL copied.");
  }

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6 sm:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="page-kicker">Lead CRM</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Pipeline</h1>
            <p className="mt-2 text-sm text-steel">Track leads from new inquiry through qualification and close.</p>
          </div>
          <div className="grid gap-3">
            <form className="flex flex-col gap-2 sm:flex-row" onSubmit={handleSearch}>
              <input
                className="focus-ring w-full px-3.5 py-2.5 text-sm md:w-72"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search name, email, source"
                value={search}
              />
              <button className="btn-secondary">
                Search
              </button>
            </form>
            <div className="flex items-center gap-2 rounded-xl border border-line bg-linen/80 px-3 py-2">
              <span className="break-all text-xs text-steel">{publicFormUrl}</span>
              <button className="btn-secondary px-3 py-1.5 text-xs" onClick={copyPublicFormUrl} type="button">
                Copy
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-5">
        {stages.map((stage) => {
          const stageLeads = leads.filter((lead) => lead.stage === stage.value);
          return (
            <div className="kanban-column p-4 transition hover:border-pine/20" key={stage.value}>
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-ink">{stage.label}</h2>
                <span className="status-pill px-2 py-1">{stageLeads.length}</span>
              </div>
              <div className="mt-4 grid gap-3">
                {stageLeads.map((lead) => (
                  <button
                    className={`kanban-card p-3 text-left transition ${selectedLead?.id === lead.id ? "border-pine bg-mint/50" : ""}`}
                    key={lead.id}
                    onClick={() => setSelectedLeadId(lead.id)}
                    type="button"
                  >
                    <p className="text-sm font-semibold text-ink">{lead.name ?? lead.email}</p>
                    <p className="mt-1 break-all text-xs text-steel">{lead.email}</p>
                    <p className="mt-2 text-xs text-steel">{lead.source ?? "No source"}</p>
                    <select
                      className="focus-ring mt-3 w-full px-2 py-1.5 text-xs"
                      onChange={(event) => moveLead(lead.id, event.target.value as LeadStage)}
                      onClick={(event) => event.stopPropagation()}
                      value={lead.stage}
                    >
                      {stages.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </button>
                ))}
                {stageLeads.length === 0 ? <p className="empty-state p-3 text-xs">No leads</p> : null}
              </div>
            </div>
          );
        })}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="surface-card p-6">
          <h2 className="text-lg font-semibold text-ink">Add lead</h2>
          <form className="mt-4 grid gap-4" onSubmit={handleCreate}>
            <div className="grid gap-4 md:grid-cols-3">
              <input className="focus-ring px-3.5 py-2.5 text-sm" onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Name" value={form.name} />
              <input className="focus-ring px-3.5 py-2.5 text-sm" onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} placeholder="Email" required type="email" value={form.email} />
              <input className="focus-ring px-3.5 py-2.5 text-sm" onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} placeholder="Phone" value={form.phone} />
              <input className="focus-ring px-3.5 py-2.5 text-sm" onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))} placeholder="Source" value={form.source} />
              <input className="focus-ring px-3.5 py-2.5 text-sm md:col-span-2" onChange={(event) => setForm((current) => ({ ...current, tags: event.target.value }))} placeholder="Tags separated by commas" value={form.tags} />
            </div>
            {message ? <p className="alert-success">{message}</p> : null}
            {error ? <p className="alert-error">{error}</p> : null}
            <button className="btn-primary w-fit" disabled={saving}>
              {saving ? "Saving..." : "Add lead"}
            </button>
          </form>
        </div>

        <aside className="surface-card p-6">
          <h2 className="text-lg font-semibold text-ink">Lead details</h2>
          {selectedLead ? (
            <div className="mt-4 grid gap-3">
              <div>
                <p className="font-semibold text-ink">{selectedLead.name ?? "-"}</p>
                <p className="mt-1 break-all text-sm text-steel">{selectedLead.email}</p>
              </div>
              <div className="grid gap-2 text-sm text-steel">
                <p>Phone: {selectedLead.phone ?? "-"}</p>
                <p>Source: {selectedLead.source ?? "-"}</p>
                <p>Tags: {selectedLead.tags.join(", ") || "-"}</p>
                <p>Last contacted: {selectedLead.last_contacted_at ? new Date(selectedLead.last_contacted_at).toLocaleString() : "-"}</p>
              </div>
              <textarea
                className="focus-ring min-h-32 px-3.5 py-2.5 text-sm"
                onChange={(event) => setNotesDraft(event.target.value)}
                placeholder="Notes"
                value={notesDraft}
              />
              <button className="btn-primary" onClick={saveNotes} type="button">
                Save notes
              </button>
            </div>
          ) : (
            <p className="mt-3 text-sm text-steel">Select a lead to view details.</p>
          )}
        </aside>
      </section>

      <section className="surface-card p-6">
        <h2 className="text-lg font-semibold text-ink">Lead list</h2>
        <div className="table-wrap">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase text-steel">
              <tr>
                <th className="py-3 pr-4">Name</th>
                <th className="py-3 pr-4">Email</th>
                <th className="py-3 pr-4">Phone</th>
                <th className="py-3 pr-4">Source</th>
                <th className="py-3 pr-4">Stage</th>
                <th className="py-3 pr-4">Tags</th>
                <th className="py-3 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr className="border-b border-line/70" key={lead.id}>
                  <td className="py-3 pr-4 font-medium text-ink">{lead.name ?? "-"}</td>
                  <td className="py-3 pr-4 text-steel">{lead.email}</td>
                  <td className="py-3 pr-4 text-steel">{lead.phone ?? "-"}</td>
                  <td className="py-3 pr-4 text-steel">{lead.source ?? "-"}</td>
                  <td className="py-3 pr-4 text-steel">{lead.stage}</td>
                  <td className="py-3 pr-4 text-steel">{lead.tags.join(", ") || "-"}</td>
                  <td className="flex gap-2 py-3 pr-4">
                    <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => setSelectedLeadId(lead.id)} type="button">Details</button>
                    <button className="focus-ring rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50" onClick={() => handleDelete(lead.id)} type="button">Delete</button>
                  </td>
                </tr>
              ))}
              {!loading && leads.length === 0 ? <tr><td className="py-5 text-steel" colSpan={7}>No leads found.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
