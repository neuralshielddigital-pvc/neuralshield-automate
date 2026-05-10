"use client";

import { FormEvent, useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  activateCampaign,
  createCampaign,
  deleteCampaign,
  getCampaigns,
  getCampaignStats,
  pauseCampaign,
  updateCampaign
} from "@/lib/campaigns";
import type { Campaign, CampaignStats, CampaignType } from "@/lib/types";

const blankForm = {
  name: "",
  type: "EMAIL" as CampaignType,
  subject: "",
  message: ""
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [form, setForm] = useState(blankForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function loadData() {
    setError("");
    try {
      const [campaignResponse, statsResponse] = await Promise.all([getCampaigns(), getCampaignStats()]);
      setCampaigns(campaignResponse.items);
      setStats(statsResponse);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load campaigns.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (editingId) {
        await updateCampaign(editingId, form);
      } else {
        await createCampaign(form);
      }
      setForm(blankForm);
      setEditingId(null);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save campaign.");
    } finally {
      setSaving(false);
    }
  }

  function startEdit(campaign: Campaign) {
    setEditingId(campaign.id);
    setForm({
      name: campaign.name,
      type: campaign.type,
      subject: campaign.subject ?? "",
      message: campaign.message
    });
  }

  async function runAction(action: () => Promise<unknown>) {
    setError("");
    try {
      await action();
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed.");
    }
  }

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6 sm:p-8">
        <p className="page-kicker">Campaign automation</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Campaigns</h1>
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          {[
            ["Campaigns", stats?.campaigns ?? 0],
            ["Active", stats?.active_campaigns ?? 0],
            ["Leads", stats?.leads ?? 0],
            ["Workflows", stats?.workflows ?? 0]
          ].map(([label, value]) => (
            <div className="metric-card" key={label}>
              <p className="text-xs font-semibold uppercase text-steel">{label}</p>
              <p className="mt-2 text-xl font-semibold text-ink">{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-card p-6">
        <h2 className="text-lg font-semibold text-ink">{editingId ? "Edit campaign" : "Create campaign"}</h2>
        <form className="mt-4 grid gap-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-3">
            <input
              className="focus-ring px-3.5 py-2.5 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              placeholder="Campaign name"
              required
              value={form.name}
            />
            <select
              className="focus-ring px-3.5 py-2.5 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, type: event.target.value as CampaignType }))}
              value={form.type}
            >
              <option value="EMAIL">Email</option>
              <option value="SMS">SMS</option>
              <option value="WHATSAPP">WhatsApp</option>
            </select>
            <input
              className="focus-ring px-3.5 py-2.5 text-sm"
              onChange={(event) => setForm((current) => ({ ...current, subject: event.target.value }))}
              placeholder="Subject"
              value={form.subject}
            />
          </div>
          <textarea
            className="focus-ring min-h-28 px-3.5 py-2.5 text-sm"
            onChange={(event) => setForm((current) => ({ ...current, message: event.target.value }))}
            placeholder="Message"
            required
            value={form.message}
          />
          {error ? <p className="alert-error">{error}</p> : null}
          <div className="flex gap-3">
            <button className="btn-primary" disabled={saving}>
              {saving ? "Saving..." : editingId ? "Update campaign" : "Create campaign"}
            </button>
            {editingId ? (
              <button className="btn-secondary" onClick={() => { setEditingId(null); setForm(blankForm); }} type="button">
                Cancel
              </button>
            ) : null}
          </div>
        </form>
      </section>

      <section className="surface-card p-6">
        <h2 className="text-lg font-semibold text-ink">Campaign list</h2>
        <div className="table-wrap">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase text-steel">
              <tr>
                <th className="py-3 pr-4">Name</th>
                <th className="py-3 pr-4">Type</th>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Subject</th>
                <th className="py-3 pr-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign) => (
                <tr className="border-b border-line/70" key={campaign.id}>
                  <td className="py-3 pr-4 font-medium text-ink">{campaign.name}</td>
                  <td className="py-3 pr-4 text-steel">{campaign.type}</td>
                  <td className="py-3 pr-4 text-steel">{campaign.status}</td>
                  <td className="py-3 pr-4 text-steel">{campaign.subject ?? "-"}</td>
                  <td className="flex flex-wrap gap-2 py-3 pr-4">
                    <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => startEdit(campaign)}>Edit</button>
                    <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => runAction(() => activateCampaign(campaign.id))}>Activate</button>
                    <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => runAction(() => pauseCampaign(campaign.id))}>Pause</button>
                    <button className="focus-ring rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50" onClick={() => runAction(() => deleteCampaign(campaign.id))}>Delete</button>
                  </td>
                </tr>
              ))}
              {!loading && campaigns.length === 0 ? (
                <tr><td className="py-5 text-steel" colSpan={5}>No campaigns yet.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
