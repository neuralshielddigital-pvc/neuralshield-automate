"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useSearchParams } from "next/navigation";

import { AuthCard } from "@/components/auth-card";
import { ApiError } from "@/lib/api";
import {
  resendVerificationEmail,
  signup,
} from "@/lib/auth";
import { clearTokens } from "@/lib/token-storage";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.detail === "string"
      ? error.detail
      : "Signup failed. Please try again.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Signup failed. Please try again.";
}

export function SignupForm() {
  const searchParams = useSearchParams();
  const referralCode = searchParams.get("ref");

  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [submittedEmail, setSubmittedEmail] =
    useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [accountCreated, setAccountCreated] =
    useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (loading || accountCreated) {
      return;
    }

    setError("");
    setMessage("");
    setLoading(true);

    const normalizedEmail = email.trim().toLowerCase();

    try {
      await signup(
        normalizedEmail,
        password,
        tenantName,
        referralCode,
      );

      // Signup currently returns auth tokens for backward compatibility.
      // Unverified users should not retain an authenticated browser session.
      clearTokens();

      setSubmittedEmail(normalizedEmail);
      setAccountCreated(true);
      setPassword("");
    } catch (signupError) {
      setError(getErrorMessage(signupError));
    } finally {
      setLoading(false);
    }
  }

  async function handleResendVerification() {
    if (!submittedEmail || resending) {
      return;
    }

    setError("");
    setMessage("");
    setResending(true);

    try {
      const response = await resendVerificationEmail(
        submittedEmail,
      );

      setMessage(response.message);
    } catch (resendError) {
      setError(getErrorMessage(resendError));
    } finally {
      setResending(false);
    }
  }

  if (accountCreated) {
    return (
      <AuthCard
        footerCta="Return to login"
        footerHref="/login"
        footerText="Already verified your email?"
        subtitle="Your workspace has been created. Verify your email before signing in."
        title="Check your email"
      >
        <div className="grid gap-5">
          <div
            className="alert-success"
            role="status"
          >
            Account created successfully.
          </div>

          <div className="rounded-xl border border-line bg-linen/70 px-4 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-steel">
              Verification email sent to
            </p>

            <p className="mt-2 break-all font-semibold text-ink">
              {submittedEmail}
            </p>
          </div>

          <p className="text-sm leading-6 text-steel">
            Open the verification link in your email. The
            link expires after 24 hours and can only be used
            once.
          </p>

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
            disabled={resending}
            onClick={() =>
              void handleResendVerification()
            }
            type="button"
          >
            {resending
              ? "Sending verification email..."
              : "Resend verification email"}
          </button>

          <Link
            href="/login"
            className="btn-secondary py-3 text-center"
          >
            Return to login
          </Link>

          <p className="text-xs leading-5 text-steel">
            Email nahi mila ho to spam or junk folder bhi
            check karein. Resend karne par purana unused link
            invalidate ho jayega.
          </p>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      footerCta="Login"
      footerHref="/login"
      footerText="Already have an account?"
      subtitle="Create your automation workspace and verify your business email."
      title="Create workspace"
    >
      <form
        className="grid gap-4"
        onSubmit={handleSubmit}
      >
        <label className="grid gap-2 text-sm font-medium text-ink">
          Company name
          <input
            autoComplete="organization"
            className="focus-ring px-3.5 py-3 text-sm"
            disabled={loading}
            maxLength={150}
            minLength={2}
            onChange={(event) =>
              setTenantName(event.target.value)
            }
            required
            value={tenantName}
          />
        </label>

        <label className="grid gap-2 text-sm font-medium text-ink">
          Email
          <input
            autoComplete="email"
            className="focus-ring px-3.5 py-3 text-sm"
            disabled={loading}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            required
            type="email"
            value={email}
          />
        </label>

        <label className="grid gap-2 text-sm font-medium text-ink">
          Password
          <input
            autoComplete="new-password"
            className="focus-ring px-3.5 py-3 text-sm"
            disabled={loading}
            maxLength={128}
            minLength={12}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            required
            type="password"
            value={password}
          />
        </label>

        <div className="rounded-xl border border-line bg-linen/70 px-4 py-3 text-xs leading-5 text-steel">
          Password must include at least 12 characters,
          uppercase, lowercase, a number, and a special
          character.
        </div>

        {referralCode ? (
          <p className="rounded-lg border border-pine/15 bg-mint px-3 py-2 text-sm font-semibold text-pine">
            Referral code applied: {referralCode}
          </p>
        ) : null}

        {error ? (
          <p
            className="alert-error"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <button
          className="btn-primary py-3"
          disabled={loading}
          type="submit"
        >
          {loading
            ? "Creating workspace..."
            : "Create workspace"}
        </button>

        <p className="text-xs leading-5 text-steel">
          By creating an account, you agree to verify your
          email before accessing the workspace.
        </p>
      </form>
    </AuthCard>
  );
}
