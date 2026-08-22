import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service | NeuralShieldDigital",
  description:
    "Review the terms governing use of the NeuralShieldDigital automation platform, subscriptions, integrations, APIs, and AI features.",
};

const sections = [
  {
    title: "1. Agreement to These Terms",
    content: (
      <>
        <p>
          These Terms of Service (&quot;Terms&quot;) govern your access to and
          use of the NeuralShieldDigital website, automation platform,
          integrations, APIs, templates, billing services, and related features
          (collectively, the &quot;Service&quot;).
        </p>

        <p>
          By creating an account, accessing the Service, or using any paid or
          free feature, you agree to these Terms and our Privacy Policy. If you
          do not agree, you must not use the Service.
        </p>
      </>
    ),
  },
  {
    title: "2. Business Use and Eligibility",
    content: (
      <>
        <p>
          The Service is intended primarily for businesses, agencies,
          consultants, professionals, and authorized representatives of
          organizations.
        </p>

        <p>
          You must be legally capable of entering into a binding agreement and
          must be at least 18 years old, or the minimum legal age required in
          your jurisdiction.
        </p>

        <p>
          If you use the Service on behalf of an organization, you represent
          that you have authority to bind that organization to these Terms.
        </p>
      </>
    ),
  },
  {
    title: "3. Accounts and Workspace Security",
    content: (
      <>
        <p>
          You must provide accurate account information and keep it current.
          You are responsible for all activity performed through your account,
          workspace, API keys, webhook URLs, connected applications, and user
          credentials.
        </p>

        <p>
          You must protect passwords, API keys, access tokens, webhook URLs, and
          other credentials from unauthorized access. You must notify us
          promptly if you suspect a security incident or unauthorized use.
        </p>

        <p>
          We may require email verification, additional authentication, or
          security checks before allowing access to certain features.
        </p>
      </>
    ),
  },
  {
    title: "4. Acceptable Use",
    content: (
      <>
        <p>You may not use the Service to:</p>

        <ul>
          <li>Violate any applicable law, regulation, or third-party right.</li>
          <li>
            Send spam, phishing messages, fraudulent content, malware, or
            unauthorized communications.
          </li>
          <li>
            Access, monitor, scrape, probe, or interfere with systems without
            authorization.
          </li>
          <li>
            Circumvent usage limits, security controls, authentication, rate
            limits, or billing restrictions.
          </li>
          <li>
            Process unlawful, deceptive, abusive, discriminatory, defamatory,
            or harmful content.
          </li>
          <li>
            Use the Service to make fully automated high-impact decisions where
            human review is legally required.
          </li>
          <li>
            Copy, reverse engineer, resell, or exploit the Service except as
            expressly permitted.
          </li>
          <li>
            Use another person&apos;s credentials, API keys, workspace, or
            connected account without authorization.
          </li>
        </ul>
      </>
    ),
  },
  {
    title: "5. Workflows and Automations",
    content: (
      <>
        <p>
          You are responsible for the workflows you create, activate, install,
          import, or execute, including their triggers, actions, conditions,
          recipients, destinations, prompts, and data-processing behavior.
        </p>

        <p>
          You must test workflows before production use and monitor execution
          logs, failures, retries, duplicate actions, external API responses,
          and downstream effects.
        </p>

        <p>
          Automated actions may cause emails to be sent, data to be modified,
          external requests to be made, messages to be posted, or third-party
          systems to be updated. You remain responsible for these outcomes.
        </p>
      </>
    ),
  },
  {
    title: "6. Workflow Templates",
    content: (
      <>
        <p>
          Templates are provided as starting points and may require
          configuration before use. You are responsible for reviewing and
          testing all installed templates.
        </p>

        <p>
          We do not guarantee that a template is appropriate for your business,
          legal obligations, industry, security requirements, or connected
          systems.
        </p>
      </>
    ),
  },
  {
    title: "7. Third-Party Integrations",
    content: (
      <>
        <p>
          The Service may connect with third-party services such as Google,
          Gmail, Google Sheets, Slack, OpenAI, Paddle, and other providers.
        </p>

        <p>
          Your use of third-party services is governed by their own terms,
          privacy policies, API limitations, availability, and account
          requirements. We do not control third-party services and are not
          responsible for their downtime, policy changes, revoked permissions,
          data loss, pricing changes, API limitations, or security incidents.
        </p>

        <p>
          You are responsible for maintaining valid third-party accounts and
          permissions required by your workflows.
        </p>
      </>
    ),
  },
  {
    title: "8. Google and Slack Connections",
    content: (
      <>
        <p>
          When you connect Google or Slack, you authorize the Service to access
          and process information within the scopes you approve for the purpose
          of running requested automation features.
        </p>

        <p>
          You may disconnect an integration through the dashboard or revoke
          access through the applicable third-party provider.
        </p>

        <p>
          Disconnecting or revoking access may cause related triggers and
          actions to stop working.
        </p>
      </>
    ),
  },
  {
    title: "9. Artificial Intelligence Features",
    content: (
      <>
        <p>
          AI-generated content may be incomplete, inaccurate, outdated,
          misleading, offensive, or unsuitable for your intended use.
        </p>

        <p>
          You must review AI outputs before using them for customer
          communications, business decisions, legal matters, financial matters,
          healthcare matters, employment decisions, compliance decisions, or
          other important purposes.
        </p>

        <p>
          You are responsible for the prompts, content, data, instructions, and
          outputs associated with AI actions. AI output is not legal, financial,
          medical, compliance, or professional advice.
        </p>
      </>
    ),
  },
  {
    title: "10. API Keys, Webhooks, and Developer Access",
    content: (
      <>
        <p>
          API keys and webhook URLs must be treated as confidential credentials.
          You must not expose them in frontend code, public repositories, shared
          screenshots, public logs, support forums, or chat messages.
        </p>

        <p>
          You are responsible for revoking compromised API keys and rotating
          exposed webhook credentials promptly.
        </p>

        <p>
          We may apply authentication requirements, rate limits, quotas,
          versioning, access restrictions, and other controls to APIs and
          webhook services.
        </p>
      </>
    ),
  },
  {
    title: "11. Free and Paid Plans",
    content: (
      <>
        <p>
          The Service may offer free and paid plans with different workflow,
          execution, integration, template, support, and usage limits.
        </p>

        <p>
          Current plan limits, pricing, and included features are displayed on
          the website or billing dashboard. We may modify plans, pricing, or
          included features by providing reasonable notice where required.
        </p>

        <p>
          Usage limits may be enforced automatically. Workflows may be blocked,
          paused, limited, or rejected when account or plan limits are reached.
        </p>
      </>
    ),
  },
  {
    title: "12. Billing and Paddle Payments",
    content: (
      <>
        <p>
          Paid subscriptions are processed through Paddle or another payment
          provider that we may designate in the future.
        </p>

        <p>
          By purchasing a subscription, you authorize the applicable payment
          provider to process the charges displayed during checkout. You are
          responsible for applicable taxes, banking charges, foreign exchange
          charges, and payment-provider fees unless stated otherwise.
        </p>

        <p>
          Subscription activation is subject to successful payment,
          verification of the payment signature, order details, amount,
          currency, and other security checks.
        </p>

        <p>
          Failed, reversed, disputed, fraudulent, duplicated, or incomplete
          payments may result in delayed activation, suspension, cancellation,
          or correction of the subscription.
        </p>
      </>
    ),
  },
  {
    title: "13. Renewals, Changes, and Cancellation",
    content: (
      <>
        <p>
          Subscription renewal terms are displayed during checkout or in the
          billing dashboard. Where recurring billing is enabled, your plan may
          renew until cancelled.
        </p>

        <p>
          You may request cancellation or manage available billing actions from
          the dashboard or by contacting support.
        </p>

        <p>
          Cancellation normally stops future renewal and does not automatically
          create a refund for the current billing period, except where required
          by law or expressly approved by us.
        </p>
      </>
    ),
  },
  {
    title: "14. Refunds",
    content: (
      <>
        <p>
          Refund requests are reviewed based on payment status, service usage,
          duplicate charges, technical issues, applicable law, and the
          circumstances of the request.
        </p>

        <p>
          Approved refunds are processed through the original payment provider
          and may require additional processing time by banks or payment
          networks.
        </p>

        <p>
          We may reject refund requests involving abuse, fraud, excessive
          usage, policy violations, expired eligibility periods, or services
          already materially consumed, except where applicable law requires
          otherwise.
        </p>
      </>
    ),
  },
  {
    title: "15. Customer Data",
    content: (
      <>
        <p>
          As between you and NeuralShieldDigital, you retain your rights in the
          business data, workflow data, content, and instructions that you
          submit to the Service.
        </p>

        <p>
          You grant us a limited right to host, process, transmit, reproduce,
          and use that data only as necessary to provide, secure, maintain, and
          improve the Service, comply with law, and enforce these Terms.
        </p>

        <p>
          You represent that you have all rights, permissions, notices, and
          lawful bases required to provide and process such data.
        </p>
      </>
    ),
  },
  {
    title: "16. Intellectual Property",
    content: (
      <>
        <p>
          The Service, platform code, design, branding, documentation, templates,
          interfaces, software, and related intellectual property are owned by
          NeuralShieldDigital or its licensors.
        </p>

        <p>
          Subject to these Terms, we grant you a limited, revocable,
          non-exclusive, non-transferable right to use the Service for your
          internal business purposes during the applicable subscription period.
        </p>

        <p>
          No ownership rights are transferred to you except for rights expressly
          granted in these Terms.
        </p>
      </>
    ),
  },
  {
    title: "17. Feedback",
    content: (
      <p>
        If you provide ideas, suggestions, or feedback, you grant us permission
        to use them without restriction or compensation, provided that we do not
        publicly identify you without permission.
      </p>
    ),
  },
  {
    title: "18. Service Availability and Changes",
    content: (
      <>
        <p>
          We aim to provide a reliable Service but do not guarantee uninterrupted,
          error-free, or continuous availability.
        </p>

        <p>
          We may perform maintenance, deploy updates, change features, modify
          integrations, apply limits, or discontinue functionality when
          reasonably necessary.
        </p>

        <p>
          Workflow execution may be affected by infrastructure failures,
          third-party downtime, internet failures, API changes, expired OAuth
          permissions, rate limits, invalid configuration, or events outside our
          reasonable control.
        </p>
      </>
    ),
  },
  {
    title: "19. Suspension and Termination",
    content: (
      <>
        <p>
          We may suspend, limit, or terminate access if we reasonably believe
          that you violated these Terms, failed to pay required fees, created a
          security risk, abused the platform, violated law, or caused harm to
          users, third parties, or the Service.
        </p>

        <p>
          You may stop using the Service at any time. Certain provisions,
          including payment obligations, intellectual property, disclaimers,
          liability limitations, and dispute terms, survive termination.
        </p>
      </>
    ),
  },
  {
    title: "20. Disclaimer of Warranties",
    content: (
      <>
        <p>
          To the maximum extent permitted by law, the Service is provided
          &quot;as is&quot; and &quot;as available.&quot;
        </p>

        <p>
          We disclaim warranties of merchantability, fitness for a particular
          purpose, non-infringement, accuracy, uninterrupted availability,
          error-free operation, and fitness of workflow or AI outputs for your
          intended use.
        </p>

        <p>
          Nothing in these Terms excludes warranties or rights that cannot
          legally be excluded.
        </p>
      </>
    ),
  },
  {
    title: "21. Limitation of Liability",
    content: (
      <>
        <p>
          To the maximum extent permitted by law, NeuralShieldDigital will not
          be liable for indirect, incidental, special, consequential,
          exemplary, punitive, or similar damages, including loss of profits,
          revenue, goodwill, data, business opportunities, or expected savings.
        </p>

        <p>
          Our aggregate liability arising from or relating to the Service will
          not exceed the amount you paid to NeuralShieldDigital for the Service
          during the three months immediately preceding the event giving rise
          to the claim, unless applicable law requires a different limit.
        </p>

        <p>
          These limitations do not apply to liability that cannot legally be
          limited or excluded.
        </p>
      </>
    ),
  },
  {
    title: "22. Indemnification",
    content: (
      <p>
        To the extent permitted by law, you agree to defend, indemnify, and hold
        harmless NeuralShieldDigital and its personnel from claims, losses,
        liabilities, damages, costs, and expenses arising from your workflows,
        content, customer data, misuse of the Service, violation of these Terms,
        violation of law, or infringement of third-party rights.
      </p>
    ),
  },
  {
    title: "23. Governing Law and Disputes",
    content: (
      <>
        <p>
          These Terms are governed by the laws applicable to the legal entity
          operating NeuralShieldDigital, without regard to conflict-of-law
          principles.
        </p>

        <p>
          Before initiating formal proceedings, you agree to contact us and
          attempt in good faith to resolve the dispute informally.
        </p>

        <p>
          The final governing-law jurisdiction, courts, arbitration provisions,
          and company registration details should be confirmed before commercial
          launch and may be updated in these Terms.
        </p>
      </>
    ),
  },
  {
    title: "24. Regional Consumer Rights",
    content: (
      <p>
        Nothing in these Terms limits consumer, privacy, refund, cancellation,
        or statutory rights that cannot legally be waived under the laws of your
        jurisdiction, including applicable rights in the United States, United
        Kingdom, European Economic Area, Canada, Australia, and New Zealand.
      </p>
    ),
  },
  {
    title: "25. Changes to These Terms",
    content: (
      <>
        <p>
          We may update these Terms to reflect changes in the Service, law,
          security, integrations, billing, or business operations.
        </p>

        <p>
          The updated version will be posted on this page with a revised
          effective date. Material changes may also be communicated through the
          Service or by email.
        </p>
      </>
    ),
  },
  {
    title: "26. Contact",
    content: (
      <>
        <p>For questions about these Terms, contact:</p>

        <p>
          <strong>NeuralShieldDigital</strong>
          <br />
          Email:{" "}
          <a
            className="font-semibold text-[#0f6b57] hover:underline"
            href="mailto:support@neuralshielddigital.com"
          >
            support@neuralshielddigital.com
          </a>
        </p>
      </>
    ),
  },
];

export default function TermsPage() {
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
            Terms of Service
          </h1>

          <p className="mt-5 text-base leading-7 text-black/60">
            These Terms govern your use of the NeuralShieldDigital automation
            platform, integrations, APIs, templates, subscriptions, and related
            services.
          </p>

          <p className="mt-4 text-sm font-semibold text-black/55">
            Effective date: July 15, 2026
          </p>
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[250px_1fr]">
        <aside className="hidden lg:block">
          <div className="sticky top-6 max-h-[calc(100vh-3rem)] overflow-y-auto rounded-2xl border border-black/10 bg-white p-5">
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

          <div className="flex flex-wrap gap-5">
            <Link href="/" className="hover:text-[#0f6b57]">
              Home
            </Link>

            <Link href="/privacy" className="hover:text-[#0f6b57]">
              Privacy
            </Link>

            <Link href="/signup" className="hover:text-[#0f6b57]">
              Start free
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
