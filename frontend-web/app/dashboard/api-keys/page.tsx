"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, apiRequest } from "@/lib/api";

type ApiKey = {
  id: string;
  name: string;
  status: string;
  is_active: boolean;
  created_at: string;
};

export default function ApiKeysPage() {
  const [items, setItems] = useState<ApiKey[]>([]);
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [explorerKey, setExplorerKey] = useState("");
  const [explorerLoading, setExplorerLoading] = useState(false);
  const [explorerStatus, setExplorerStatus] = useState<number | null>(null);
  const [explorerResponse, setExplorerResponse] = useState("");

async function copyKey() {
  if (!newKey) return;

  await navigator.clipboard.writeText(newKey);
  alert("API key copied to clipboard.");
}

async function runApiExplorer() {
  const apiKey = explorerKey.trim();

  if (!apiKey) {
    setExplorerStatus(null);
    setExplorerResponse(
      JSON.stringify(
        { detail: "Enter an API key before sending the request." },
        null,
        2
      )
    );
    return;
  }

  setExplorerLoading(true);
  setExplorerStatus(null);
  setExplorerResponse("");

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    setExplorerStatus(response.status);

    const responseText = await response.text();

    try {
      setExplorerResponse(
        JSON.stringify(JSON.parse(responseText), null, 2)
      );
    } catch {
      setExplorerResponse(
        responseText || "No response body returned."
      );
    }
  } catch {
    setExplorerStatus(null);
    setExplorerResponse(
      JSON.stringify(
        {
          detail:
            "Could not reach the API. Check your connection and try again.",
        },
        null,
        2
      )
    );
  } finally {
    setExplorerLoading(false);
  }
}

async function copyExplorerResponse() {
  if (!explorerResponse) return;

  await navigator.clipboard.writeText(explorerResponse);
}

  async function load() {
    const res = await apiRequest<{ items: ApiKey[] }>("/api/api-keys");
    setItems(res.items ?? []);
  }

  useEffect(() => {
    load();
  }, []);

  async function createKey() {
    if (!name.trim()) return;

    setLoading(true);

    try {
      const res = await apiRequest<{
        api_key: string;
      }>("/api/api-keys", {
        method: "POST",
        body: JSON.stringify({
          name,
        }),
      });

      setNewKey(res.api_key);
      setName("");
      await load();
    } finally {
      setLoading(false);
    }
  }

  async function revoke(id: string) {
  const ok = window.confirm(
    "Are you sure?\n\nThis API key will immediately stop working."
  );

  if (!ok) return;

  await apiRequest(`/api/api-keys/${id}`, {
    method: "DELETE",
  });

  await load();
}

  return (
    <div className="grid gap-6">

      <section className="surface-card p-6">
        <h1 className="text-3xl font-bold">
          API Keys
        </h1>

        <p className="mt-2 text-sm text-steel">
          Create secure API keys for your applications.
        </p>
      </section>

      <section className="surface-card p-6">

        <div className="flex gap-3">

          <input
            className="input flex-1"
            placeholder="Key name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <button
            className="btn-primary"
            disabled={loading}
            onClick={createKey}
          >
            Create Key
          </button>

        </div>

        {newKey && (
  <div className="mt-6 rounded-xl border border-emerald-300 bg-emerald-50 p-5">

    <div className="flex items-center gap-2">
      <span aria-hidden="true">🔑</span>
      <p className="font-semibold">
        Copy this key now. It will never be shown again.
      </p>
    </div>

    <pre className="mt-4 overflow-x-auto rounded bg-white p-3 text-xs">
{newKey}
    </pre>

    <button
      className="btn-primary mt-4 flex items-center gap-2"
      onClick={copyKey}
    >
      📋 Copy API Key
    </button>

  </div>
)}

      </section>

      <section className="surface-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-pine">
              API Explorer
            </p>

            <h2 className="mt-1 text-xl font-semibold text-ink">
              Test GET /api/v1/me
            </h2>

            <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">
              Enter a temporary API key and send a live request. The key stays
              only in this page state and is not saved by the explorer.
            </p>
          </div>

          <span className="rounded-full border border-line bg-linen px-3 py-1.5 text-xs font-semibold text-steel">
            Bearer authentication
          </span>
        </div>

        <div className="mt-6 grid gap-4">
          <div>
            <label
              className="text-sm font-semibold text-ink"
              htmlFor="api-explorer-key"
            >
              API key
            </label>

            <input
              id="api-explorer-key"
              className="input mt-2 w-full font-mono text-sm"
              onChange={(event) => setExplorerKey(event.target.value)}
              placeholder="nsd_..."
              type="password"
              value={explorerKey}
            />

            <p className="mt-2 text-xs leading-5 text-steel">
              Never use an exposed or shared key. Revoke test keys after use.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              className="btn-primary"
              disabled={explorerLoading || !explorerKey.trim()}
              onClick={runApiExplorer}
              type="button"
            >
              {explorerLoading ? "Sending..." : "Send Request"}
            </button>

            <button
              className="btn-secondary"
              onClick={() => {
                setExplorerKey("");
                setExplorerStatus(null);
                setExplorerResponse("");
              }}
              type="button"
            >
              Clear
            </button>
          </div>

          {explorerResponse ? (
            <div className="mt-2">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-sm font-semibold text-ink">
                    Live response
                  </h3>

                  {explorerStatus !== null ? (
                    <span
                      className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                        explorerStatus >= 200 && explorerStatus < 300
                          ? "border-pine/20 bg-mint text-pine"
                          : "border-red-200 bg-red-50 text-red-700"
                      }`}
                    >
                      HTTP {explorerStatus}
                    </span>
                  ) : null}
                </div>

                <button
                  className="btn-secondary px-3 py-1.5 text-xs"
                  onClick={copyExplorerResponse}
                  type="button"
                >
                  Copy Response
                </button>
              </div>

              <pre className="max-h-96 overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
                <code>{explorerResponse}</code>
              </pre>
            </div>
          ) : null}
        </div>
      </section>

      <section className="surface-card p-6">

        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="text-left p-2">Name</th>
              <th className="text-left p-2">Status</th>
              <th className="text-left p-2">Created</th>
              <th className="text-left p-2">Action</th>
            </tr>
          </thead>

          <tbody>

            {items.map((item) => (
              <tr key={item.id}>
                <td className="p-2">{item.name}</td>
                <td className="p-2">{item.status}</td>
                <td className="p-2">
                  {new Date(item.created_at).toLocaleString()}
                </td>
                <td className="p-2">
                  {item.is_active && (
                    <button
  className="btn-secondary flex items-center gap-2"
  onClick={() => revoke(item.id)}
>
  🗑️ Revoke
</button>
                  )}
                </td>
              </tr>
            ))}

            {items.length === 0 && (
              <tr>
                <td colSpan={4} className="p-4 text-center">
                  <div className="py-8 text-center">

  <p className="mb-3 text-3xl" aria-hidden="true">🔑</p>

  <p className="font-semibold">
    No API Keys yet
  </p>

  <p className="mt-2 text-sm text-steel">
    Create your first API key to access the NeuralShield API.
  </p>

</div>
                </td>
              </tr>
            )}

          </tbody>
        </table>

      </section>

    </div>
  );
}
