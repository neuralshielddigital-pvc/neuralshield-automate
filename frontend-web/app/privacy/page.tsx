import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy | NeuralShieldDigital",
  description:
    "Learn how NeuralShieldDigital collects, uses, protects, and manages personal information across its automation platform.",
};

const sections = [
  {
    title: "1. Scope of this Privacy Policy",
    content: (
      <>
        <p>
          This Privacy Policy explains how NeuralShieldDigital
          (&quot;NeuralShieldDigital,&quot; &quot;we,&quot; &quot;us,&quot; or
          &quot;our&quot;) collects, uses, stores, discloses, and protects
          information when you visit our website, create an account, use our
          automation platform, connect third-party integrations, or communicate
          with us.
        </p>
        <p>
          This Policy applies to customers and visitors in the United States,
          United Kingdom, European Economic Area, Canada, Australia, New Zealand,
          and other regions where our services are available.
        </p>
      </>
    ),
  },
  {
    title: "2. Information We Collect",
    content: (
      <>
        <p>We may collect the following categories of information:</p>

        <ul>
          <li>
            <strong>Account information:</strong> name, email address, password
            hash, workspace details, user role, and account status.
          </li>
          <li>
            <strong>Billing information:</strong> subscription plan, transaction
            identifiers, payment status, billing history, and limited payment
            metadata supplied by payment providers such as Paddle or Digistore24.
            We do not store full card numbers.
          </li>
          <li>
            <strong>Workflow information:</strong> workflow names, triggers,
            actions, configuration, execution history, logs, and error details.
          </li>
          <li>
            <strong>Lead and business data:</strong> information submitted to
            workflows, webhooks, lead forms, campaigns, and connected services.
          </li>
          <li>
            <strong>Integration information:</strong> connected account email,
            workspace name, OAuth scopes, encrypted access tokens, encrypted
            refresh tokens, and synchronization state.
          </li>
          <li>
            <strong>Technical information:</strong> IP address, browser type,
            device information, request identifiers, timestamps, and security
            logs.
          </li>
          <li>
            <strong>Support information:</strong> messages and information you
            provide when requesting help.
          </li>
        </ul>
      </>
    ),
  },
  {
    title: "3. How We Use Information",
    content: (
      <>
        <p>We use information to:</p>

        <ul>
          <li>Provide, operate, maintain, and secure the platform.</li>
          <li>Authenticate users and manage workspaces and permissions.</li>
          <li>Create, execute, monitor, and troubleshoot workflows.</li>
          <li>Connect and operate third-party integrations you authorize.</li>
          <li>Process subscriptions, payments, upgrades, and refunds.</li>
          <li>Apply workflow and monthly usage limits.</li>
          <li>Prevent fraud, abuse, unauthorized access, and security incidents.</li>
          <li>Provide customer support and service communications.</li>
          <li>Improve reliability, performance, usability, and documentation.</li>
          <li>Comply with legal, regulatory, and contractual obligations.</li>
        </ul>
      </>
    ),
  },
  {
    title: "4. Google User Data",
    content: (
      <>
        <p>
          When you connect Google, the platform may request access to Gmail and
          other Google services only for features you choose to use, such as
          detecting matching emails, sending emails, or appending information to
          Google Sheets.
        </p>

        <p>
          Google OAuth tokens are encrypted at rest. We do not sell Google user
          data, use it for advertising, or transfer it for unrelated purposes.
          Access is limited to providing and improving user-facing features,
          maintaining security, complying with law, or acting with your explicit
          authorization.
        </p>

        <p>
          Our use and transfer of information received from Google APIs will
          comply with the Google API Services User Data Policy, including its
          Limited Use requirements.
        </p>

        <p>
          You may disconnect Google from the Integrations page. You may also
          revoke access through your Google Account security settings.
        </p>
      </>
    ),
  },
  {
    title: "5. Slack User Data",
    content: (
      <>
        <p>
          When you connect Slack, we may process your Slack workspace name,
          authorized scopes, encrypted OAuth tokens, message identifiers,
          channel identifiers, and message content required to run the workflows
          you configure.
        </p>

        <p>
          Slack information is used only to provide requested trigger and action
          functionality, maintain security, troubleshoot failures, and comply
          with applicable law.
        </p>

        <p>
          You may disconnect Slack from the Integrations page or revoke the app
          from your Slack workspace administration settings.
        </p>
      </>
    ),
  },
  {
    title: "6. Artificial Intelligence Features",
    content: (
      <>
        <p>
          When a workflow uses an AI action, the content configured for that
          action may be sent to an AI service provider, such as OpenAI, to
          generate the requested output.
        </p>

        <p>
          You are responsible for ensuring that information submitted to an AI
          action may lawfully be processed and does not contain unnecessary
          sensitive, confidential, regulated, or restricted information.
        </p>
      </>
    ),
  },
  {
    title: "7. API Keys and Webhooks",
    content: (
      <>
        <p>
          API keys are shown only when created and are stored by us as secure
          cryptographic hashes. You are responsible for protecting API keys,
          webhook URLs, and other credentials associated with your account.
        </p>

        <p>
          If an API key or webhook endpoint is exposed, you should revoke or
          replace it immediately.
        </p>
      </>
    ),
  },
  {
    title: "8. How We Share Information",
    content: (
      <>
        <p>
          We do not sell personal information. We may share limited information
          with service providers that help us operate the platform, including:
        </p>

        <ul>
          <li>Cloud and hosting providers, including AWS and Cloudflare.</li>
          <li>Database infrastructure providers, including Neon.</li>
          <li>Payment processors and merchants of record, including Paddle and Digistore24.</li>
          <li>Email delivery providers.</li>
          <li>Integration providers, including Google and Slack.</li>
          <li>AI service providers when you use AI workflow actions.</li>
          <li>Monitoring, logging, security, and support service providers.</li>
        </ul>

        <p>
          We may also disclose information where required by law, legal process,
          regulatory request, enforcement action, security investigation, or to
          protect the rights and safety of users, NeuralShieldDigital, or others.
        </p>
      </>
    ),
  },
  {
    title: "9. Legal Bases for Processing",
    content: (
      <>
        <p>
          Where the GDPR or UK GDPR applies, we process personal information
          under one or more of the following legal bases:
        </p>

        <ul>
          <li>Performance of a contract.</li>
          <li>Compliance with a legal obligation.</li>
          <li>Our legitimate interests in operating and securing the service.</li>
          <li>Your consent, where consent is required.</li>
        </ul>
      </>
    ),
  },
  {
    title: "10. International Data Transfers",
    content: (
      <>
        <p>
          NeuralShieldDigital and its service providers may process information
          in countries other than the country where you live. These countries
          may have different data-protection laws.
        </p>

        <p>
          Where required, we use appropriate safeguards for international data
          transfers, such as contractual protections or other legally recognized
          transfer mechanisms.
        </p>
      </>
    ),
  },
  {
    title: "11. Data Retention",
    content: (
      <>
        <p>
          We retain information only for as long as reasonably necessary to
          provide the service, maintain security, resolve disputes, enforce
          agreements, comply with law, and preserve required business records.
        </p>

        <p>
          Retention periods may differ depending on the type of information,
          account status, contractual requirements, and legal obligations.
          Backup copies may remain for a limited period before being securely
          overwritten or deleted.
        </p>
      </>
    ),
  },
  {
    title: "12. Security",
    content: (
      <>
        <p>
          We use administrative, technical, and organizational safeguards
          designed to protect information. Current controls include HTTPS,
          encryption of integration credentials, hashed passwords and API keys,
          tenant isolation, role-based access controls, rate limiting, security
          headers, backups, audit logs, and infrastructure monitoring.
        </p>

        <p>
          No system is completely secure. You are responsible for maintaining
          strong account credentials, protecting API keys, and promptly reporting
          suspected unauthorized access.
        </p>
      </>
    ),
  },
  {
    title: "13. Cookies and Local Storage",
    content: (
      <>
        <p>
          We may use essential cookies or browser storage required for
          authentication, session management, security, user preferences, and
          core platform functionality.
        </p>

        <p>
          If optional analytics or advertising technologies are introduced, we
          will provide additional notice and consent controls where required.
        </p>
      </>
    ),
  },
  {
    title: "14. Your Privacy Rights",
    content: (
      <>
        <p>
          Depending on your location, you may have rights to request access,
          correction, deletion, restriction, portability, objection, withdrawal
          of consent, or information about how personal data is processed.
        </p>

        <p>
          Residents of California and other applicable US states may have
          additional rights regarding access, deletion, correction, and disclosure
          of personal information. We do not sell personal information or share
          it for cross-context behavioral advertising.
        </p>

        <p>
          Individuals in Australia may have rights under the Privacy Act 1988 and
          the Australian Privacy Principles. Individuals in Canada may have
          rights under applicable federal or provincial privacy laws.
        </p>

        <p>
          We may need to verify your identity before completing a request.
          Certain rights may be limited where an exception applies.
        </p>
      </>
    ),
  },
  {
    title: "15. Children’s Privacy",
    content: (
      <p>
        The service is intended for businesses and is not directed to children
        under 16. We do not knowingly collect personal information from children.
        If you believe a child has provided information, contact us so that we
        can review and delete it where appropriate.
      </p>
    ),
  },
  {
    title: "16. Account Deletion and Integration Removal",
    content: (
      <>
        <p>
          You may disconnect Google or Slack from the Integrations page and
          revoke API keys from the API Keys page.
        </p>

        <p>
          To request account deletion or deletion of personal information,
          contact us using the details below. Some information may be retained
          where necessary for legal, security, fraud-prevention, billing, or
          dispute-resolution purposes.
        </p>
      </>
    ),
  },
  {
    title: "17. Changes to this Policy",
    content: (
      <p>
        We may update this Privacy Policy as the platform, laws, or business
        practices change. The updated version will be posted on this page with a
        revised effective date. Material changes may also be communicated through
        the platform or by email.
      </p>
    ),
  },
  {
    title: "18. Contact Us",
    content: (
      <>
        <p>
          For privacy questions, rights requests, or account deletion requests,
          contact:
        </p>

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
            Privacy Policy
          </h1>

          <p className="mt-5 text-base leading-7 text-black/60">
            This Policy explains how NeuralShieldDigital handles information
            when you use our website, automation platform, integrations, APIs,
            and related services.
          </p>

          <p className="mt-4 text-sm font-semibold text-black/55">
            Effective date: July 15, 2026
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
              Start free
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
