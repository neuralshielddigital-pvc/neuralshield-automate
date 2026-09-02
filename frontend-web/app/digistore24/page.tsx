import type { Metadata } from "next";
import Link from "next/link";
import Digistore24Badges from "@/components/digistore24-badges";

export const metadata: Metadata = {
  title: "AI Workflow Automation — Starter",
  description:
    "Automate repetitive business workflows with NeuralShieldDigital. Starter is $19 per month through Digistore24.",
  robots: {
    index: true,
    follow: true,
  },
};

const CHECKOUT_URL =
  "https://www.checkout-ds24.com/product/728732";

const features = [
  "10 active workflows",
  "500 automation runs per month",
  "Unlimited webhooks",
  "Gmail, Slack and Google Sheets integrations",
  "AI workflow actions",
  "Workflow template marketplace",
  "Email support",
];

export default function Digistore24SalesPage() {
  return (
    <main className="min-h-screen px-5 py-10 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <Link
            href="/"
            className="text-xl font-bold text-pine"
          >
            NeuralShieldDigital
          </Link>

          <nav className="flex gap-4 text-sm font-semibold text-steel">
            <Link href="/terms">Terms</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/contact">Support</Link>
          </nav>
        </header>

        <section className="py-16 text-center">
          <p className="page-kicker">AI Workflow Automation</p>

          <h1 className="mx-auto mt-4 max-w-4xl text-4xl font-bold tracking-tight text-ink sm:text-6xl">
            Automate repetitive business work without building everything from scratch.
          </h1>

          <p className="mx-auto mt-6 max-w-3xl text-lg leading-8 text-steel">
            NeuralShield AI Workflow Automation is a cloud-based SaaS platform
            for building and running business workflows with integrations,
            webhooks, scheduling and AI-powered actions.
          </p>

          <div className="mx-auto mt-10 max-w-xl surface-card p-8 text-left">
            <p className="text-sm font-bold uppercase text-pine">
              Starter Plan
            </p>

            <div className="mt-3 flex items-end gap-2">
              <span className="text-5xl font-bold text-ink">$19</span>
              <span className="pb-1 text-steel">/ month</span>
            </div>

            <p className="mt-3 text-sm leading-6 text-steel">
              Billed monthly according to the payment schedule shown during
              Digistore24 checkout. Future recurring payments can be cancelled.
            </p>

            <ul className="mt-6 space-y-3 text-sm text-ink">
              {features.map((feature) => (
                <li key={feature} className="flex gap-3">
                  <span aria-hidden="true">✓</span>
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <a
              href={CHECKOUT_URL}
              className="btn-primary mt-8 block w-full text-center"
              rel="nofollow"
            >
              Start Starter for $19/month
            </a>

            <p className="mt-4 text-center text-xs leading-5 text-steel">
              Secure checkout and payment processing are provided by
              Digistore24.
            </p>
          </div>
        </section>

        <section className="grid gap-6 pb-12 md:grid-cols-3">
          <article className="surface-card p-6">
            <h2 className="text-xl font-semibold text-ink">
              Built for practical workflows
            </h2>
            <p className="mt-3 text-sm leading-6 text-steel">
              Connect supported tools, configure triggers and actions, test
              workflows and monitor execution from the dashboard.
            </p>
          </article>

          <article className="surface-card p-6">
            <h2 className="text-xl font-semibold text-ink">
              Cloud-based access
            </h2>
            <p className="mt-3 text-sm leading-6 text-steel">
              No physical product is shipped and no local software download is
              required. Access the application through your web browser.
            </p>
          </article>

          <article className="surface-card p-6">
            <h2 className="text-xl font-semibold text-ink">
              60-day refund policy
            </h2>
            <p className="mt-3 text-sm leading-6 text-steel">
              Digistore24 purchases for this offer are configured with a
              60-day refund period, subject to applicable terms and payment
              provider rules.
            </p>
          </article>
        </section>

        <section className="surface-card mb-12 p-8">
          <h2 className="text-2xl font-semibold text-ink">
            After purchase
          </h2>
          <p className="mt-4 leading-7 text-steel">
            After checkout, follow the access instructions on the confirmation
            page and sign in or create your NeuralShieldDigital workspace at
            app.neuralshielddigital.com.
          </p>

          <p className="mt-4 text-sm text-steel">
            Support:{" "}
            <a
              className="font-semibold text-pine"
              href="mailto:support@neuralshielddigital.com"
            >
              support@neuralshielddigital.com
            </a>
          </p>
        </section>

        <section className="mb-12 space-y-5">
          <Digistore24Badges placement="trust" />
        </section>

        <footer className="border-t border-sand py-8 text-sm text-steel">
          <div className="mb-6">
            <Digistore24Badges placement="footer" />
          </div>
          <div className="flex flex-wrap justify-between gap-4">
            <span>© NeuralShield Digital Pvt Ltd</span>

            <div className="flex flex-wrap gap-4">
              <Link href="/terms">Terms</Link>
              <Link href="/privacy">Privacy</Link>
              <Link href="/contact">Contact</Link>
            </div>
          </div>
        </footer>
      </div>
    </main>
  );
}
