"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { AuthCard } from "@/components/auth-card";
import { ApiError } from "@/lib/api";
import { forgotPassword } from "@/lib/auth";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.detail === "string"
      ? error.detail
      : "Could not request a password reset.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Could not request a password reset.";
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await forgotPassword(email);

      setMessage(response.message);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      footerCta="Back to login"
      footerHref="/login"
      footerText="Remembered your password?"
      subtitle="Enter your account email and we will send a secure password reset link."
      title="Forgot your password?"
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
            ? "Sending reset link..."
            : "Send reset link"}
        </button>

        <p className="text-xs leading-5 text-steel">
          For security, we show the same response whether
          or not an account exists for the email.
        </p>

        <Link
          href="/login"
          className="text-center text-sm font-semibold text-pine hover:underline"
        >
          Return to sign in
        </Link>
      </form>
    </AuthCard>
  );
}
