"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  getAffiliateCommissions,
  getAffiliateMe,
  getAffiliateReferrals,
  getAffiliateStats,
  registerAffiliate
} from "@/lib/affiliate";
import type { AffiliateCommission, AffiliateMeResponse, AffiliateReferral, AffiliateStats } from "@/lib/types";

const emptyStats: AffiliateStats = {
  total_referrals: 0,
  pending_commissions: "0.00",
  approved_commissions: "0.00",
  paid_commissions: "0.00"
};

export default function AffiliatePage() {
  const [affiliateMe, setAffiliateMe] = useState<AffiliateMeResponse | null>(null);
  const [stats, setStats] = useState<AffiliateStats>(emptyStats);
  const [referrals, setReferrals] = useState<AffiliateReferral[]>([]);
  const [commissions, setCommissions] = useState<AffiliateCommission[]>([]);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  async function loadAffiliateData() {
    setError("");
    try {
      const me = await getAffiliateMe();
      setAffiliateMe(me);
      if (me.is_registered) {
        const [statsResponse, referralsResponse, commissionsResponse] = await Promise.all([
          getAffiliateStats(),
          getAffiliateReferrals(),
          getAffiliateCommissions()
        ]);
        setStats(statsResponse);
        setReferrals(referralsResponse);
        setCommissions(commissionsResponse);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load affiliate data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAffiliateData();
  }, []);

  async function handleRegister() {
    setRegistering(true);
    setError("");
    try {
      const response = await registerAffiliate();
      setAffiliateMe(response);
      await loadAffiliateData();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not register as affiliate.");
    } finally {
      setRegistering(false);
    }
  }

  async function handleCopy() {
    if (!affiliateMe?.referral_link) return;
    await navigator.clipboard.writeText(affiliateMe.referral_link);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  const registered = affiliateMe?.is_registered;

  return (
    <div className="grid gap-6">
      <section className="surface-card p-6 sm:p-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="page-kicker">Affiliate</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Partner dashboard</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
              Share your referral link, track referred signups, and monitor commission status.
            </p>
          </div>
          {!loading && !registered ? (
            <button
              className="btn-primary"
              disabled={registering}
              onClick={handleRegister}
              type="button"
            >
              {registering ? "Registering..." : "Register as affiliate"}
            </button>
          ) : null}
        </div>

        {error ? <p className="alert-error mt-5">{error}</p> : null}

        {registered ? (
          <div className="mt-6 grid gap-4 rounded-xl border border-line bg-linen/80 p-4">
            <div>
              <p className="text-xs font-semibold uppercase text-steel">Referral code</p>
              <p className="mt-1 text-lg font-semibold text-ink">{affiliateMe.affiliate?.referral_code}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-steel">Referral link</p>
              <div className="mt-2 flex flex-col gap-3 sm:flex-row">
                <input
                  className="focus-ring min-w-0 flex-1 px-3.5 py-2.5 text-sm"
                  readOnly
                  value={affiliateMe.referral_link ?? ""}
                />
                <button
                  className="btn-secondary"
                  onClick={handleCopy}
                  type="button"
                >
                  {copied ? "Copied" : "Copy link"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </section>

      {registered ? (
        <>
          <section className="grid gap-4 md:grid-cols-4">
            {[
              ["Total referrals", stats.total_referrals],
              ["Pending commissions", `$${stats.pending_commissions}`],
              ["Approved commissions", `$${stats.approved_commissions}`],
              ["Paid commissions", `$${stats.paid_commissions}`]
            ].map(([label, value]) => (
              <div className="metric-card" key={label}>
                <p className="text-xs font-semibold uppercase text-steel">{label}</p>
                <p className="mt-2 text-xl font-semibold text-ink">{value}</p>
              </div>
            ))}
          </section>

          <section className="surface-card p-6">
            <h2 className="text-lg font-semibold text-ink">Referrals</h2>
            <div className="table-wrap">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="border-b border-line text-xs uppercase text-steel">
                  <tr>
                    <th className="py-3 pr-4">Email</th>
                    <th className="py-3 pr-4">Referred at</th>
                    <th className="py-3 pr-4">User ID</th>
                  </tr>
                </thead>
                <tbody>
                  {referrals.map((referral) => (
                    <tr className="border-b border-line/70" key={referral.id}>
                      <td className="py-3 pr-4 font-medium text-ink">{referral.referred_user_email}</td>
                      <td className="py-3 pr-4 text-steel">{new Date(referral.created_at).toLocaleString()}</td>
                      <td className="py-3 pr-4 text-steel">{referral.referred_user_id}</td>
                    </tr>
                  ))}
                  {referrals.length === 0 ? (
                    <tr>
                      <td className="py-5 text-steel" colSpan={3}>
                        No referrals yet.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

          <section className="surface-card p-6">
            <h2 className="text-lg font-semibold text-ink">Commissions</h2>
            <div className="table-wrap">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead className="border-b border-line text-xs uppercase text-steel">
                  <tr>
                    <th className="py-3 pr-4">Amount</th>
                    <th className="py-3 pr-4">Status</th>
                    <th className="py-3 pr-4">Created</th>
                    <th className="py-3 pr-4">Referral ID</th>
                  </tr>
                </thead>
                <tbody>
                  {commissions.map((commission) => (
                    <tr className="border-b border-line/70" key={commission.id}>
                      <td className="py-3 pr-4 font-semibold text-ink">${commission.amount}</td>
                      <td className="py-3 pr-4 text-steel">{commission.status}</td>
                      <td className="py-3 pr-4 text-steel">{new Date(commission.created_at).toLocaleString()}</td>
                      <td className="py-3 pr-4 text-steel">{commission.referral_id}</td>
                    </tr>
                  ))}
                  {commissions.length === 0 ? (
                    <tr>
                      <td className="py-5 text-steel" colSpan={4}>
                        No commissions yet.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : loading ? (
        <p className="surface-card flex items-center gap-3 p-6 text-sm text-steel">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-pine" />
          Loading affiliate data...
        </p>
      ) : null}
    </div>
  );
}
