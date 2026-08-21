"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthCard } from "@/components/auth-card";
import { ApiError } from "@/lib/api";
import { login } from "@/lib/auth";

function isEmailVerificationError(error: unknown): boolean {
  if (!(error instanceof ApiError)) {
    return false;
  }

  const detail =
    typeof error.detail === "string"
      ? error.detail.toLowerCase()
      : "";

  return (
    error.status === 403 &&
    detail.includes("verify your email")
  );
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.detail === "string"
      ? error.detail
      : "Login failed. Please try again.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Login failed. Please try again.";
}

function getSafeNextPath(): string {
  if (typeof window === "undefined") {
    return "/dashboard";
  }

  const next = new URLSearchParams(
    window.location.search,
  ).get("next");

  if (
    !next ||
    !next.startsWith("/") ||
    next.startsWith("//") ||
    next.startsWith("/\\")
  ) {
    return "/dashboard";
  }

  try {
    const parsed = new URL(
      next,
      window.location.origin,
    );

    if (parsed.origin !== window.location.origin) {
      return "/dashboard";
    }

    return (
      parsed.pathname +
      parsed.search +
      parsed.hash
    );
  } catch {
    return "/dashboard";
  }
}

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [verificationRequired, setVerificationRequired] =
    useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setVerificationRequired(false);
    setLoading(true);

    try {
      await login(email, password);

      router.replace(getSafeNextPath());
      router.refresh();
    } catch (loginError) {
      setVerificationRequired(
        isEmailVerificationError(loginError),
      );
      setError(getErrorMessage(loginError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      footerCta="Create account"
      footerHref="/signup"
      footerText="New to NeuralShieldDigital?"
      subtitle="Sign in to manage your automations, integrations, usage, and billing."
      title="Welcome back"
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
            required
            type="email"
            value={email}
          />
        </label>

        <div className="grid gap-2">
          <div className="flex items-center justify-between gap-3">
            <label
              className="text-sm font-medium text-ink"
              htmlFor="password"
            >
              Password
            </label>

            <Link
              href="/forgot-password"
              className="text-xs font-semibold text-pine hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          <input
            id="password"
            autoComplete="current-password"
            className="focus-ring px-3.5 py-3 text-sm"
            disabled={loading}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            required
            type="password"
            value={password}
          />
        </div>

        {error ? (
          <div
            className="alert-error"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        {verificationRequired ? (
          <div className="grid gap-3 rounded-xl border border-pine/20 bg-mint/50 p-4">
            <p className="text-sm leading-6 text-steel">
              Aapka password correct hai, lekin email
              verification abhi pending hai.
            </p>

            <Link
              href="/resend-verification"
              className="btn-secondary py-3 text-center"
            >
              Resend verification email
            </Link>
          </div>
        ) : null}

        <button
          className="btn-primary py-3"
          disabled={loading}
          type="submit"
        >
          {loading ? "Signing in..." : "Login"}
        </button>
      </form>
    </AuthCard>
  );
}
