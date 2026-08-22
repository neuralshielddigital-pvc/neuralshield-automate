"use client";

import Link from "next/link";
import {
  Suspense,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useSearchParams } from "next/navigation";

import { AuthCard } from "@/components/auth-card";
import { ApiError } from "@/lib/api";
import { verifyEmail } from "@/lib/auth";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.detail === "string"
      ? error.detail
      : "Email verification failed.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Email verification failed.";
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();

  const token = useMemo(
    () => searchParams.get("token")?.trim() ?? "",
    [searchParams],
  );

  const [status, setStatus] = useState<
    "loading" | "success" | "error"
  >("loading");

  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;

    async function runVerification() {
      if (!token) {
        if (active) {
          setStatus("error");
          setMessage(
            "This verification link is invalid or incomplete.",
          );
        }

        return;
      }

      try {
        const response = await verifyEmail(token);

        if (active) {
          setStatus("success");
          setMessage(response.message);
        }
      } catch (error) {
        if (active) {
          setStatus("error");
          setMessage(getErrorMessage(error));
        }
      }
    }

    void runVerification();

    return () => {
      active = false;
    };
  }, [token]);

  return (
    <AuthCard
      footerCta="Return to login"
      footerHref="/login"
      footerText="Ready to access your workspace?"
      subtitle="We are confirming your NeuralShieldDigital account email."
      title="Verify your email"
    >
      <div className="grid gap-5">
        {status === "loading" ? (
          <div
            className="rounded-xl border border-line bg-linen/70 px-4 py-5 text-sm text-steel"
            role="status"
          >
            Verifying your email address...
          </div>
        ) : null}

        {status === "success" ? (
          <>
            <div
              className="alert-success"
              role="status"
            >
              {message || "Email verified successfully."}
            </div>

            <p className="text-sm leading-6 text-steel">
              Your email address is verified. You can now
              continue to your NeuralShieldDigital workspace.
            </p>

            <Link
              href="/login"
              className="btn-primary py-3 text-center"
            >
              Sign in to your workspace
            </Link>
          </>
        ) : null}

        {status === "error" ? (
          <>
            <div
              className="alert-error"
              role="alert"
            >
              {message}
            </div>

            <p className="text-sm leading-6 text-steel">
              The link may have expired, already been used, or
              be incomplete. Request a new verification email.
            </p>

            <Link
              href="/resend-verification"
              className="btn-primary py-3 text-center"
            >
              Request new verification email
            </Link>

            <Link
              href="/login"
              className="btn-secondary py-3 text-center"
            >
              Return to login
            </Link>
          </>
        ) : null}
      </div>
    </AuthCard>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <AuthCard
          footerCta="Return to login"
          footerHref="/login"
          footerText="Ready to access your workspace?"
          subtitle="Loading your secure verification link."
          title="Verify your email"
        >
          <div className="text-sm text-steel">
            Loading...
          </div>
        </AuthCard>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
