import type { Metadata } from "next";
import Link from "next/link";
import Digistore24Badges from "@/components/digistore24-badges";

export const metadata: Metadata = {
  title: "AI Workflow Automation Plans",
  description:
    "Choose Starter, Pro, or Business for NeuralShield AI Workflow Automation. Secure checkout is provided by Digistore24.",
  robots: {
    index: true,
    follow: true,
  },
};

const CHECKOUT_URL = "https://www.checkout-ds24.com/product/728732";

const plans = [
  {
    name: "Starter",
    price: "$19",
    description:
      "For solo founders and small businesses getting started with workflow automation.",
    badge: "",
    features: [
      "10 active workflows",
      "500 automation runs / month",
      "Unlimited webhooks",
      "Gmail, Slack & Google Sheets",
      "AI workflow actions",
      "Workflow template marketplace",
      "Email support",
    ],
  },
  {
    name: "Pro",
    price: "$59",
    description:
      "For growing teams that need more workflows, automation capacity, and advanced capabilities.",
    badge: "Most Popular",
    features: [
      "50 active workflows",
      "20,000 automation runs / month",
      "Everything in Starter",
      "Premium workflow templates",
      "API access",
      "Priority support",
      "Advanced AI automation",
    ],
  },
  {
    name: "Business",
    price: "$149",
    description:
      "For businesses that need team collaboration and substantially higher automation capacity.",
    badge: "",
    features: [
      "Unlimited active workflows",
      "100,000 automation runs / month",
      "Everything in Pro",
      "Team access",
      "Advanced analytics",
      "API access",
      "Dedicated onboarding",
    ],
  },
];

export default function Digistore24SalesPage() {
  return (
    <main className="min-h-screen px-5 py-10 sm:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <Link href="/" className="text-xl font-bold text-pine">
            NeuralShieldDigital
          </Link>

          <nav className="flex gap-4 text-sm font-semibold text-steel">
            <Link href="/terms">Terms</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/contact">Support</Link>
          </nav>
        </header>

        <section className="py-16 text-center">
          <p className="page-kicker">AI WORKFLOW AUTOMATION</p>

          <h1 className="mx-auto mt-4 max-w-5xl text-4xl font-bold tracking-tight text-ink sm:text-6xl">
            Choose the automation capacity that fits your business.
          </h1>

          <p className="mx-auto mt-6 max-w-3xl text-lg leading-8 text-steel">
            Build and run business workflows with integrations, webhooks,
            scheduling and AI-powered actions. Choose your preferred plan
            securely during Digistore24 checkout.
          </p>
        </section>

        <section className="grid gap-6 pb-12 lg:grid-cols-3">
          {plans.map((plan) => (
            <article
              key={plan.name}
              className={`surface-card relative flex flex-col p-7 ${
                plan.badge ? "ring-2 ring-pine" : ""
              }`}
            >
              {plan.badge ? (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 rounded-full bg-pine px-4 py-1 text-xs font-bold text-white">
                  {plan.badge}
                </div>
              ) : null}

              <p className="text-sm font-bold uppercase text-pine">
                {plan.name} Plan
              </p>

              <div className="mt-4 flex items-end gap-2">
                <span className="text-5xl font-bold text-ink">
                  {plan.price}
                </span>
                <span className="pb-1 text-steel">/ month</span>
              </div>

              <p className="mt-4 min-h-20 text-sm leading-6 text-steel">
                {plan.description}
              </p>

              <ul className="mt-6 flex-1 space-y-3 text-sm text-ink">
                {plan.features.map((feature) => (
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
                Choose {plan.name}
              </a>
            </article>
          ))}
        </section>

        <section className="mx-auto mb-12 max-w-4xl surface-card p-8 text-center">
          <h2 className="text-2xl font-semibold text-ink">
            One secure checkout, three plans
          </h2>

          <p className="mt-4 leading-7 text-steel">
            After clicking a plan above, Digistore24 will show Starter at
            $19/month, Pro at $59/month, and Business at $149/month. Select
            your preferred plan on the secure checkout page before completing
            your order.
          </p>

          <p className="mt-4 text-sm leading-6 text-steel">
            Each available plan is billed monthly according to the payment
            schedule displayed at checkout. Future recurring payments can be
            cancelled.
          </p>
        </section>

        <section className="grid gap-6 pb-12 md:grid-cols-3">
          <article className="surface-card p-6">
            <h2 className="text-xl font-semibold text-ink">
              Cloud-based SaaS
            </h2>
            <p className="mt-3 text-sm leading-6 text-steel">
              Access NeuralShieldDigital through your browser. No physical
              product is shipped.
            </p>
          </article>

          <article className="surface-card p-6">
            <h2 className="text-xl font-semibold text-ink">
              Secure checkout
            </h2>
            <p className="mt-3 text-sm leading-6 text-steel">
              Checkout and payment processing for this offer are provided by
              Digistore24.
            </p>
          </article>

          <article className="surface-card p-6">
            <h2 className="text-xl font-semibold text-ink">
              60-day refund policy
            </h2>
            <p className="mt-3 text-sm leading-6 text-steel">
              This Digistore24 offer is configured with a 60-day refund period,
              subject to the applicable terms and payment-provider rules.
            </p>
          </article>
        </section>

        <section className="surface-card mb-12 p-8">
          <h2 className="text-2xl font-semibold text-ink">
            What happens after purchase?
          </h2>

          <p className="mt-4 leading-7 text-steel">
            After checkout, follow the purchase confirmation and access
            instructions to sign in or create your NeuralShieldDigital
            workspace.
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

        <section className="mb-10">
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
