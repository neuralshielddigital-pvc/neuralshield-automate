"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthCard } from "@/components/auth-card";
import { ApiError } from "@/lib/api";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : err instanceof Error ? err.message : "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard
      footerCta="Create account"
      footerHref="/signup"
      footerText="New to NeuralShieldDigital?"
      subtitle="Sign in to manage your subscription and SaaS workspace."
      title="Welcome back"
    >
      <form className="grid gap-4" onSubmit={handleSubmit}>
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
            autoComplete="current-password"
            className="focus-ring px-3.5 py-3 text-sm"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        {error ? <p className="alert-error">{error}</p> : null}
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
