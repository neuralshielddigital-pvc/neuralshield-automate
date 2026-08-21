"use client";

import Link from "next/link";
import { useState } from "react";

const BASE_URL = "https://api.neuralshielddigital.com";

const curlExample = `curl -X GET \\
  "${BASE_URL}/api/v1/me" \\
  -H "Authorization: Bearer YOUR_API_KEY"`;

const successResponse = `{
  "user_id": "68469520-71e4-4afe-81ae-e62b9c35966e",
  "tenant_id": "36207a61-670a-47d3-a209-3117c684d4c9",
  "email": "user@example.com",
  "role": "USER",
  "api_version": "v1"
}`;

const unauthorizedResponse = `{
  "detail": "Invalid or revoked API key."
}`;

export default function ApiDocsPage() {
  const [copied, setCopied] = useState("");

  async function copyText(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);

      window.setTimeout(() => {
        setCopied("");
      }, 2000);
    } catch {
      setCopied("");
    }
  }

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-pine">
              Developer Platform
            </p>

            <h1 className="mt-2 text-3xl font-bold text-ink">
              API Documentation
            </h1>

            <p className="mt-3 max-w-3xl text-sm leading-6 text-steel">
              Authenticate with a NeuralShieldDigital API key and access the
              versioned public API. Keep every API key private and revoke it
              immediately if it is exposed.
            </p>
          </div>

          <Link className="btn-primary" href="/dashboard/api-keys/">
            Manage API Keys
          </Link>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="surface-card p-6">
          <h2 className="text-xl font-semibold text-ink">
            Getting started
          </h2>

          <div className="mt-5 grid gap-5">
            <div>
              <p className="text-sm font-semibold text-ink">
                1. Create an API key
              </p>

              <p className="mt-1 text-sm leading-6 text-steel">
                Open API Keys, enter a descriptive name, and copy the secret
                immediately. The full secret is shown only once.
              </p>
            </div>

            <div>
              <p className="text-sm font-semibold text-ink">
                2. Send it as a Bearer token
              </p>

              <p className="mt-1 text-sm leading-6 text-steel">
                Add the API key to the HTTP Authorization header. Do not place
                API keys in URLs, browser code, screenshots, logs, or public
                repositories.
              </p>
            </div>

            <div>
              <p className="text-sm font-semibold text-ink">
                3. Revoke compromised keys
              </p>

              <p className="mt-1 text-sm leading-6 text-steel">
                Revocation takes effect immediately. Requests using a revoked
                key return HTTP 401.
              </p>
            </div>
          </div>
        </div>

        <div className="surface-card p-6">
          <h2 className="text-xl font-semibold text-ink">
            API information
          </h2>

          <dl className="mt-5 grid gap-4 text-sm">
            <div className="surface-panel p-4">
              <dt className="font-semibold text-ink">Base URL</dt>
              <dd className="mt-2 break-all font-mono text-xs text-steel">
                {BASE_URL}
              </dd>
            </div>

            <div className="surface-panel p-4">
              <dt className="font-semibold text-ink">Authentication</dt>
              <dd className="mt-2 font-mono text-xs text-steel">
                Authorization: Bearer nsd_...
              </dd>
            </div>

            <div className="surface-panel p-4">
              <dt className="font-semibold text-ink">Current version</dt>
              <dd className="mt-2 text-steel">v1</dd>
            </div>

            <div className="surface-panel p-4">
              <dt className="font-semibold text-ink">Content type</dt>
              <dd className="mt-2 font-mono text-xs text-steel">
                application/json
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="surface-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-pine">
              GET
            </p>

            <h2 className="mt-1 text-xl font-semibold text-ink">
              /api/v1/me
            </h2>

            <p className="mt-2 text-sm leading-6 text-steel">
              Validates the API key and returns the authenticated user and
              tenant identity associated with that key.
            </p>
          </div>

          <span className="rounded-full border border-pine/20 bg-mint px-3 py-1.5 text-xs font-semibold text-pine">
            API key required
          </span>
        </div>

        <div className="mt-6 grid gap-6">
          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-ink">
                cURL request
              </h3>

              <button
                className="btn-secondary px-3 py-1.5 text-xs"
                onClick={() => copyText(curlExample, "curl")}
                type="button"
              >
                {copied === "curl" ? "Copied" : "Copy"}
              </button>
            </div>

            <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
              <code>{curlExample}</code>
            </pre>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-ink">
                HTTP 200 response
              </h3>

              <button
                className="btn-secondary px-3 py-1.5 text-xs"
                onClick={() => copyText(successResponse, "success")}
                type="button"
              >
                {copied === "success" ? "Copied" : "Copy"}
              </button>
            </div>

            <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
              <code>{successResponse}</code>
            </pre>
          </div>
        </div>
      </section>

      <section className="surface-card p-6">
        <h2 className="text-xl font-semibold text-ink">
          Error responses
        </h2>

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-line text-xs uppercase text-steel">
              <tr>
                <th className="py-3 pr-4">Status</th>
                <th className="py-3 pr-4">Meaning</th>
                <th className="py-3 pr-4">Resolution</th>
              </tr>
            </thead>

            <tbody>
              <tr className="border-b border-line/70">
                <td className="py-4 pr-4 font-semibold text-ink">401</td>
                <td className="py-4 pr-4 text-steel">
                  API key is missing, invalid, or revoked.
                </td>
                <td className="py-4 pr-4 text-steel">
                  Create an active key and send it in the Bearer header.
                </td>
              </tr>

              <tr className="border-b border-line/70">
                <td className="py-4 pr-4 font-semibold text-ink">429</td>
                <td className="py-4 pr-4 text-steel">
                  Too many requests.
                </td>
                <td className="py-4 pr-4 text-steel">
                  Retry after a delay and reduce request frequency.
                </td>
              </tr>

              <tr>
                <td className="py-4 pr-4 font-semibold text-ink">500</td>
                <td className="py-4 pr-4 text-steel">
                  Unexpected server error.
                </td>
                <td className="py-4 pr-4 text-steel">
                  Retry later and provide the request ID to support.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-ink">
              HTTP 401 example
            </h3>

            <button
              className="btn-secondary px-3 py-1.5 text-xs"
              onClick={() => copyText(unauthorizedResponse, "unauthorized")}
              type="button"
            >
              {copied === "unauthorized" ? "Copied" : "Copy"}
            </button>
          </div>

          <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
            <code>{unauthorizedResponse}</code>
          </pre>
        </div>
      </section>

      <section className="surface-card border border-amber-200 bg-amber-50 p-6">
        <h2 className="text-lg font-semibold text-amber-950">
          API key security
        </h2>

        <p className="mt-2 text-sm leading-6 text-amber-900">
          Store API keys only in encrypted server-side environment variables or
          a secrets manager. Never expose them in frontend JavaScript, Git
          repositories, support tickets, screenshots, or chat messages.
        </p>
      </section>
    </div>
  );
}
