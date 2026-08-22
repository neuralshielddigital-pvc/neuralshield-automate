"use client";

import { useCallback, useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";

type ConnectResponse = {
  authorization_url: string;
};

type DisconnectResponse = {
  success: boolean;
  message: string;
};

type GoogleProfile = {
  emailAddress?: string;
};

type SlackProfile = {
  provider: string;
  status: string;
  workspace: string;
};

export default function IntegrationsPage() {
  const [loadingProvider, setLoadingProvider] = useState<
    "google" | "slack" | "status" | null
  >(null);

  const [message, setMessage] = useState("");
  const [googleProfile, setGoogleProfile] =
    useState<GoogleProfile | null>(null);
  const [slackProfile, setSlackProfile] =
    useState<SlackProfile | null>(null);

  const loadIntegrationStatus = useCallback(async () => {
    setLoadingProvider("status");

    const [googleResult, slackResult] = await Promise.allSettled([
      apiRequest<GoogleProfile>(
        "/api/integrations/google/gmail/profile"
      ),
      apiRequest<SlackProfile>(
        "/api/integrations/slack/profile"
      ),
    ]);

    setGoogleProfile(
      googleResult.status === "fulfilled"
        ? googleResult.value
        : null
    );

    setSlackProfile(
      slackResult.status === "fulfilled"
        ? slackResult.value
        : null
    );

    setLoadingProvider(null);
  }, []);

  useEffect(() => {
    void loadIntegrationStatus();
  }, [loadIntegrationStatus]);

  async function connectGoogle() {
    try {
      setLoadingProvider("google");
      setMessage("");

      const response = await apiRequest<ConnectResponse>(
        "/api/integrations/google/connect"
      );

      window.location.assign(response.authorization_url);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to connect Google."
      );
      setLoadingProvider(null);
    }
  }

  async function disconnectGoogle() {
    const confirmed = window.confirm(
      "Disconnect Google?\n\nGmail and Google-based workflows may stop working until you reconnect."
    );

    if (!confirmed) {
      return;
    }

    try {
      setLoadingProvider("google");
      setMessage("");

      const response = await apiRequest<DisconnectResponse>(
        "/api/integrations/google/disconnect",
        {
          method: "DELETE",
        }
      );

      setGoogleProfile(null);
      setMessage(response.message);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to disconnect Google."
      );
    } finally {
      setLoadingProvider(null);
    }
  }

  async function connectSlack() {
    try {
      setLoadingProvider("slack");
      setMessage("");

      const response = await apiRequest<ConnectResponse>(
        "/api/integrations/slack/connect"
      );

      window.location.assign(response.authorization_url);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to connect Slack."
      );
      setLoadingProvider(null);
    }
  }

  async function disconnectSlack() {
    const confirmed = window.confirm(
      "Disconnect Slack?\n\nSlack triggers and message actions may stop working until you reconnect."
    );

    if (!confirmed) {
      return;
    }

    try {
      setLoadingProvider("slack");
      setMessage("");

      const response = await apiRequest<DisconnectResponse>(
        "/api/integrations/slack/disconnect",
        {
          method: "DELETE",
        }
      );

      setSlackProfile(null);
      setMessage(response.message);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to disconnect Slack."
      );
    } finally {
      setLoadingProvider(null);
    }
  }

  const statusLoading = loadingProvider === "status";
  const googleLoading = loadingProvider === "google";
  const slackLoading = loadingProvider === "slack";

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="page-kicker">Connected apps</p>

            <h1 className="mt-2 text-3xl font-bold text-ink">
              Integrations
            </h1>

            <p className="mt-3 max-w-2xl text-sm leading-6 text-steel">
              Connect the applications used by your workflows. Connection
              secrets are encrypted and never displayed in the dashboard.
            </p>
          </div>

          <button
            className="btn-secondary"
            disabled={loadingProvider !== null}
            onClick={() => void loadIntegrationStatus()}
            type="button"
          >
            {statusLoading ? "Checking..." : "Refresh status"}
          </button>
        </div>
      </section>

      {message ? (
        <div className="alert-success">
          {message}
        </div>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-2">
        <article className="surface-card p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-pine">
                Google Workspace
              </p>

              <h2 className="mt-2 text-xl font-semibold text-ink">
                Gmail & Google Sheets
              </h2>
            </div>

            <span
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                googleProfile
                  ? "border-pine/20 bg-mint text-pine"
                  : "border-line bg-linen text-steel"
              }`}
            >
              {statusLoading
                ? "Checking"
                : googleProfile
                  ? "Connected"
                  : "Not connected"}
            </span>
          </div>

          <p className="mt-4 text-sm leading-6 text-steel">
            Use Gmail triggers, email actions, and Google Sheets append
            actions inside your automations.
          </p>

          <dl className="mt-5 grid gap-3 text-sm">
            <div className="surface-panel p-4">
              <dt className="font-semibold text-ink">Account</dt>
              <dd className="mt-1 break-all text-steel">
                {googleProfile?.emailAddress ??
                  (googleProfile
                    ? "Connected Google account"
                    : "No account connected")}
              </dd>
            </div>

            <div className="surface-panel p-4">
              <dt className="font-semibold text-ink">Available features</dt>
              <dd className="mt-1 text-steel">
                Gmail polling, Gmail send, and Google Sheets append
              </dd>
            </div>
          </dl>

          <div className="mt-5 flex flex-wrap gap-3">
            {googleProfile ? (
              <>
                <button
                  className="btn-secondary"
                  disabled={googleLoading}
                  onClick={connectGoogle}
                  type="button"
                >
                  {googleLoading ? "Opening..." : "Reconnect"}
                </button>

                <button
                  className="btn-secondary"
                  disabled={googleLoading}
                  onClick={disconnectGoogle}
                  type="button"
                >
                  {googleLoading ? "Working..." : "Disconnect"}
                </button>
              </>
            ) : (
              <button
                className="btn-primary"
                disabled={googleLoading || statusLoading}
                onClick={connectGoogle}
                type="button"
              >
                {googleLoading ? "Opening..." : "Connect Google"}
              </button>
            )}
          </div>
        </article>

        <article className="surface-card p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-pine">
                Team communication
              </p>

              <h2 className="mt-2 text-xl font-semibold text-ink">
                Slack
              </h2>
            </div>

            <span
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                slackProfile
                  ? "border-pine/20 bg-mint text-pine"
                  : "border-line bg-linen text-steel"
              }`}
            >
              {statusLoading
                ? "Checking"
                : slackProfile
                  ? "Connected"
                  : "Not connected"}
            </span>
          </div>

          <p className="mt-4 text-sm leading-6 text-steel">
            Use Slack message triggers, alerts, notifications, and channel
            message actions in your workflows.
          </p>

          <dl className="mt-5 grid gap-3 text-sm">
            <div className="surface-panel p-4">
              <dt className="font-semibold text-ink">Workspace</dt>
              <dd className="mt-1 break-all text-steel">
                {slackProfile?.workspace ?? "No workspace connected"}
              </dd>
            </div>

            <div className="surface-panel p-4">
              <dt className="font-semibold text-ink">Available features</dt>
              <dd className="mt-1 text-steel">
                New-message triggers and channel message actions
              </dd>
            </div>
          </dl>

          <div className="mt-5 flex flex-wrap gap-3">
            {slackProfile ? (
              <>
                <button
                  className="btn-secondary"
                  disabled={slackLoading}
                  onClick={connectSlack}
                  type="button"
                >
                  {slackLoading ? "Opening..." : "Reconnect"}
                </button>

                <button
                  className="btn-secondary"
                  disabled={slackLoading}
                  onClick={disconnectSlack}
                  type="button"
                >
                  {slackLoading ? "Working..." : "Disconnect"}
                </button>
              </>
            ) : (
              <button
                className="btn-primary"
                disabled={slackLoading || statusLoading}
                onClick={connectSlack}
                type="button"
              >
                {slackLoading ? "Opening..." : "Connect Slack"}
              </button>
            )}
          </div>
        </article>
      </section>

      <section className="surface-card border border-dashed border-line p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-steel">
              Version 1.1
            </p>

            <h2 className="mt-2 text-lg font-semibold text-ink">
              More integrations after launch
            </h2>

            <p className="mt-2 text-sm leading-6 text-steel">
              Shopify will be the first major integration in Version 1.1.
              Additional business apps will follow based on customer demand.
            </p>
          </div>

          <span className="rounded-full border border-line bg-linen px-3 py-1.5 text-xs font-semibold text-steel">
            Coming soon
          </span>
        </div>
      </section>
    </div>
  );
}
