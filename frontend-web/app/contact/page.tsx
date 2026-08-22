import type { Metadata } from "next";
import Link from "next/link";

const sections = [
  {
    title: "Customer Support",
    content: (
      <>
        <p>
          Our support team helps with account access, workflows, integrations,
          billing questions, API issues, and technical troubleshooting.
        </p>

        <ul>
          <li>Email: support@neuralshielddigital.com</li>
          <li>Response target: within one business day</li>
          <li>Priority support available on Business plans</li>
        </ul>
      </>
    ),
  },

  {
    title: "Sales & Enterprise",
    content: (
      <>
        <p>
          Contact our sales team for enterprise deployments, custom onboarding,
          implementation assistance, migration planning, and volume pricing.
        </p>

        <ul>
          <li>Email: sales@neuralshielddigital.com</li>
          <li>Custom integrations</li>
          <li>Enterprise onboarding</li>
          <li>Volume licensing</li>
        </ul>
      </>
    ),
  },

  {
    title: "Partnerships",
    content: (
      <>
        <p>
          We welcome technology partnerships, integration partners, agencies,
          consulting firms, and affiliate collaborations.
        </p>

        <ul>
          <li>Affiliate Program</li>
          <li>Technology Partners</li>
          <li>Agency Partners</li>
        </ul>
      </>
    ),
  },

  {
    title: "Security",
    content: (
      <>
        <p>
          If you discover a security vulnerability, please report it privately.
        </p>

        <ul>
          <li>security@neuralshielddigital.com</li>
          <li>Responsible disclosure</li>
          <li>No public disclosure before remediation</li>
        </ul>
      </>
    ),
  },

  {
    title: "Regions We Serve",
    content: (
      <>
        <p>
          NeuralShieldDigital provides automation services for businesses
          globally, with primary focus on:
        </p>

        <ul>
          <li>United States</li>
          <li>United Kingdom</li>
          <li>Europe</li>
          <li>Australia</li>
          <li>Canada</li>
          <li>New Zealand</li>
        </ul>
      </>
    ),
  },
];
export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-[#f7f5ee] text-[#17241f]">
      <header className="border-b border-black/10 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0f6b57] text-sm font-bold text-white">
              NS
            </span>

            <span className="font-bold">NeuralShieldDigital</span>
          </Link>

          <Link
            href="/"
            className="rounded-xl border border-black/15 px-4 py-2 text-sm font-semibold hover:border-[#0f6b57]/40"
          >
            Back to home
          </Link>
        </div>
      </header>

      <section className="border-b border-black/10 bg-white">
        <div className="mx-auto max-w-4xl px-5 py-16 sm:px-8">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
            Legal
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">
            Contact
          </h1>

          <p className="mt-5 text-base leading-7 text-black/60">
            Contact our sales, customer success, enterprise, partnership, and security teams.
          </p>

          <p className="mt-4 text-sm font-semibold text-black/55">
            Last updated: July 15, 2026
          </p>
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[250px_1fr]">
        <aside className="hidden lg:block">
          <div className="sticky top-6 rounded-2xl border border-black/10 bg-white p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-[#0f6b57]">
              Contents
            </p>

            <nav className="mt-4 grid gap-2 text-sm text-black/60">
              {sections.map((section, index) => (
                <a
                  key={section.title}
                  href={`#section-${index + 1}`}
                  className="hover:text-[#0f6b57]"
                >
                  {section.title}
                </a>
              ))}
            </nav>
          </div>
        </aside>

        <article className="rounded-3xl border border-black/10 bg-white p-6 shadow-sm sm:p-10">
          <div className="grid gap-10">
            {sections.map((section, index) => (
              <section
                id={`section-${index + 1}`}
                key={section.title}
                className="scroll-mt-8"
              >
                <h2 className="text-xl font-bold sm:text-2xl">
                  {section.title}
                </h2>

                <div className="mt-4 grid gap-4 text-sm leading-7 text-black/65 [&_ul]:grid [&_ul]:gap-2 [&_ul]:pl-5 [&_li]:list-disc">
                  {section.content}
                </div>
              </section>
            ))}
          </div>
        </article>
      </div>

      <footer className="border-t border-black/10 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-sm text-black/55 sm:px-8 md:flex-row md:items-center md:justify-between">
          <p>© 2026 NeuralShieldDigital. All rights reserved.</p>

          <div className="flex gap-5">
            <Link href="/" className="hover:text-[#0f6b57]">
              Home
            </Link>

            <Link href="/terms" className="hover:text-[#0f6b57]">
              Terms
            </Link>

            <Link href="/signup" className="hover:text-[#0f6b57]">
              <Link href="/terms" className="hover:text-[#0f6b57]">
  Terms
</Link>
<Link href="/contact" className="hover:text-[#0f6b57]">
  Contact
</Link>

<Link href="/contact" className="hover:text-[#0f6b57]">
  Contact
</Link>
                   Start free
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
