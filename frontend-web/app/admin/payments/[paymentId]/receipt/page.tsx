"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ApiError, apiRequest } from "@/lib/api";

type ReceiptData = {
  payment: any;
  user: any;
  plan: any;
  company: any;
};

function formatDate(value?: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function PaymentReceiptPage() {
  const params = useParams<{ paymentId: string }>();
  const [data, setData] = useState<ReceiptData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<ReceiptData>(`/api/admin/payments/${params.paymentId}/receipt`)
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Could not load receipt."));
  }, [params.paymentId]);

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between print:hidden">
          <div>
            <p className="page-kicker">ADMIN</p>
            <h1 className="mt-2 text-3xl font-semibold text-ink">Payment Receipt</h1>
          </div>
          <div className="flex gap-3">
            <button onClick={() => window.print()} className="btn-primary px-4 py-2">Print</button>
            <Link href="/admin/payments" className="btn-secondary px-4 py-2">Back</Link>
          </div>
        </div>

        {error ? <p className="alert-error">{error}</p> : null}

        {data ? (
          <section className="surface-card p-8">
            <div className="flex items-start justify-between border-b border-line pb-6">
              <div>
                <h2 className="text-2xl font-semibold text-ink">{data.company?.name}</h2>
                <p className="text-sm text-steel">{data.company?.email}</p>
              </div>
              <div className="text-right">
                <p className="text-xs uppercase text-steel">Receipt</p>
                <p className="font-semibold">{data.payment?.id}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase text-steel">Customer</p>
                <p className="font-semibold">{data.user?.email ?? "-"}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-steel">Date</p>
                <p>{formatDate(data.payment?.created_at)}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-steel">Plan</p>
                <p>{data.plan?.name ?? "-"}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-steel">Provider</p>
                <p>{data.payment?.provider ?? "-"}</p>
              </div>
            </div>

            <div className="mt-8 rounded-2xl border border-line p-6">
              <div className="flex justify-between">
                <span>Amount</span>
                <strong>{data.payment?.currency} {data.payment?.amount}</strong>
              </div>
              <div className="mt-3 flex justify-between">
                <span>Status</span>
                <strong>{data.payment?.status}</strong>
              </div>
              <div className="mt-3 flex justify-between">
                <span>Payment ID</span>
                <strong>{data.payment?.provider_payment_id ?? "-"}</strong>
              </div>
              <div className="mt-3 flex justify-between">
                <span>Order ID</span>
                <strong>{data.payment?.provider_order_id ?? "-"}</strong>
              </div>
            </div>

            <p className="mt-8 text-center text-sm text-steel">Thank you for your payment.</p>
          </section>
        ) : null}
      </div>
    </main>
  );
}
