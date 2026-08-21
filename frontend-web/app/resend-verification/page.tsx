"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { AuthCard } from "@/components/auth-card";
import { ApiError } from "@/lib/api";
import { resendVerificationEmail } from "@/lib/auth";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.detail === "string"
      ? error.detail
      : "Could not send a verification email.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Could not send a verification email.";
}

export default function ResendVerificationPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setLoading(true);
    setMessage("");
    setError("");

    try {
      const response = await resendVerificationEmail(email);

      setMessage(response.message);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      footerCta="Return to login"
      footerHref="/login"
      footerText="Already verified your email?"
      subtitle="Enter your account email and we will send a new secure verification link."
      title="Resend verification email"
    >
      <form
        className="grid gap-4"
        onSubmit={handleSubmit}
      >
        <label className="grid gap-2 text-sm font-medium text-ink">
          Email
          <input
            autoComplete="email"
            className="focus-ring px-3.5 py-3 text-sm"
            disabled={loading}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            placeholder="you@company.com"
            required
            type="email"
            value={email}
          />
        </label>

        {message ? (
          <div
            className="alert-success"
            role="status"
          >
            {message}
          </div>
        ) : null}

        {error ? (
          <div
            className="alert-error"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        <button
          className="btn-primary py-3"
          disabled={loading}
          type="submit"
        >
          {loading
            ? "Sending verification email..."
            : "Send verification email"}
        </button>

        <p className="text-xs leading-5 text-steel">
          For security, we display the same response whether
          or not an account exists for the email.
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          <Link
            href="/verify-email"
            className="btn-secondary py-3 text-center"
          >
            Open verification page
          </Link>

          <Link
            href="/login"
            className="btn-secondary py-3 text-center"
          >
            Return to login
          </Link>
        </div>
      </form>
    </AuthCard>
  );
}
