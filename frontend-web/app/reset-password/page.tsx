"use client";

import Link from "next/link";
import {
  FormEvent,
  Suspense,
  useMemo,
  useState,
} from "react";
import { useSearchParams } from "next/navigation";
import { AuthCard } from "@/components/auth-card";
import { ApiError } from "@/lib/api";
import { resetPassword } from "@/lib/auth";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.detail === "string"
      ? error.detail
      : "Could not reset your password.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Could not reset your password.";
}

function ResetPasswordForm() {
  const searchParams = useSearchParams();

  const token = useMemo(
    () => searchParams.get("token")?.trim() ?? "",
    [searchParams],
  );

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const tokenMissing = token.length === 0;

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (tokenMissing) {
      setError(
        "The password reset link is missing a valid token.",
      );
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const response = await resetPassword(
        token,
        newPassword,
      );

      setSuccess(response.message);
      setNewPassword("");
      setConfirmPassword("");
    } catch (resetError) {
      setError(getErrorMessage(resetError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      footerCta="Back to login"
      footerHref="/login"
      footerText="Already reset your password?"
      subtitle="Choose a strong new password for your NeuralShieldDigital account."
      title="Reset your password"
    >
      <form
        className="grid gap-4"
        onSubmit={handleSubmit}
      >
        {tokenMissing ? (
          <div
            className="alert-error"
            role="alert"
          >
            This password reset link is invalid or incomplete.
            Request a new reset link.
          </div>
        ) : null}

        <label className="grid gap-2 text-sm font-medium text-ink">
          New password
          <input
            autoComplete="new-password"
            className="focus-ring px-3.5 py-3 text-sm"
            disabled={loading || tokenMissing}
            minLength={12}
            onChange={(event) =>
              setNewPassword(event.target.value)
            }
            required
            type="password"
            value={newPassword}
          />
        </label>

        <label className="grid gap-2 text-sm font-medium text-ink">
          Confirm new password
          <input
            autoComplete="new-password"
            className="focus-ring px-3.5 py-3 text-sm"
            disabled={loading || tokenMissing}
            minLength={12}
            onChange={(event) =>
              setConfirmPassword(event.target.value)
            }
            required
            type="password"
            value={confirmPassword}
          />
        </label>

        <div className="rounded-xl border border-line bg-linen/70 px-4 py-3 text-xs leading-5 text-steel">
          Password must contain at least 12 characters,
          including uppercase, lowercase, a number, and a
          special character.
        </div>

        {success ? (
          <div
            className="alert-success"
            role="status"
          >
            {success}
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
          disabled={loading || tokenMissing || Boolean(success)}
          type="submit"
        >
          {loading
            ? "Resetting password..."
            : success
              ? "Password reset complete"
              : "Reset password"}
        </button>

        {success ? (
          <Link
            href="/login"
            className="btn-secondary py-3 text-center"
          >
            Sign in with new password
          </Link>
        ) : null}

        {tokenMissing ? (
          <Link
            href="/forgot-password"
            className="text-center text-sm font-semibold text-pine hover:underline"
          >
            Request a new reset link
          </Link>
        ) : null}
      </form>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <AuthCard
          footerCta="Back to login"
          footerHref="/login"
          footerText="Already have access?"
          subtitle="Loading your secure reset link."
          title="Reset your password"
        >
          <div className="text-sm text-steel">
            Loading...
          </div>
        </AuthCard>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
