"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthCard } from "@/components/auth-card";
import { ApiError } from "@/lib/api";
import { signup } from "@/lib/auth";

export function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const referralCode = searchParams.get("ref");
  const [tenantName, setTenantName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signup(email, password, tenantName, referralCode);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Signup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      footerCta="Login"
      footerHref="/login"
      footerText="Already have an account?"
      subtitle="Create your tenant workspace and start with billing setup."
      title="Create workspace"
    >
      <form className="grid gap-4" onSubmit={handleSubmit}>
        <label className="grid gap-2 text-sm font-medium text-ink">
          Company name
          <input
            autoComplete="organization"
            className="focus-ring px-3.5 py-3 text-sm"
            onChange={(event) => setTenantName(event.target.value)}
            required
            value={tenantName}
          />
        </label>
        <label className="grid gap-2 text-sm font-medium text-ink">
          Email
          <input
            autoComplete="email"
            className="focus-ring px-3.5 py-3 text-sm"
            onChange={(event) => setEmail(event.target.value)}
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
            minLength={12}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        {referralCode ? (
          <p className="rounded-lg border border-pine/15 bg-mint px-3 py-2 text-sm font-semibold text-pine">
            Referral code applied: {referralCode}
          </p>
        ) : null}
        {error ? <p className="alert-error">{error}</p> : null}
        <button
          className="btn-primary py-3"
          disabled={loading}
          type="submit"
        >
          {loading ? "Creating..." : "Sign up"}
        </button>
      </form>
    </AuthCard>
  );
}
