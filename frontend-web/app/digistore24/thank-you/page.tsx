import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Purchase Confirmed",
  description:
    "Access instructions for NeuralShield AI Workflow Automation purchases made through Digistore24.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function Digistore24ThankYouPage() {
  return (
    <main className="min-h-screen px-5 py-14 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="surface-card p-8 sm:p-10">
          <p className="page-kicker">Purchase confirmation</p>

          <h1 className="mt-4 text-4xl font-bold text-ink">
            Thank you for your purchase.
          </h1>

          <p className="mt-6 leading-7 text-steel">
            Your purchase of NeuralShield AI Workflow Automation was processed
            through Digistore24.
          </p>

          <div className="mt-6 rounded-2xl border border-sand bg-linen p-5">
            <p className="font-semibold text-ink">
              Your credit card statement will show a charge from Digistore24.
            </p>
          </div>

          <h2 className="mt-8 text-2xl font-semibold text-ink">
            Access your SaaS account
          </h2>

          <ol className="mt-4 space-y-3 text-steel">
            <li>1. Open the NeuralShieldDigital application.</li>
            <li>
              2. Sign in with your existing account or create a workspace using
              the email address associated with your purchase.
            </li>
            <li>
              3. Follow any purchase-verification or onboarding instructions
              provided after checkout.
            </li>
          </ol>

          <Link
            href="/login"
            className="btn-primary mt-8 inline-block"
          >
            Go to NeuralShieldDigital
          </Link>

          <p className="mt-8 text-sm leading-6 text-steel">
            For account access, billing or technical support, contact{" "}
            <a
              className="font-semibold text-pine"
              href="mailto:support@neuralshielddigital.com"
            >
              support@neuralshielddigital.com
            </a>
            .
          </p>

          <div className="mt-8 flex flex-wrap gap-4 text-sm font-semibold text-pine">
            <Link href="/terms">Terms</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/contact">Contact</Link>
          </div>
        </div>
      </div>
    </main>
  );
}
