import Link from "next/link";
import Image from "next/image";
import {
  Zap,
  Brain,
  ShieldCheck,
  BarChart3,
  Link2,
  Workflow,
} from "lucide-react";


const integrations = [
  {
    name: "Gmail",
    description: "Trigger workflows from new emails and filtered messages.",
  },
  {
    name: "Slack",
    description: "Send alerts, summaries, and operational updates to channels.",
  },
  {
    name: "Google Sheets",
    description: "Append lead, campaign, and workflow data automatically.",
  },
  {
    name: "OpenAI",
    description: "Generate summaries, replies, classifications, and AI outputs.",
  },
];

const automationExamples = [
  {
    title: "Gmail to Slack",
    description:
      "Notify your team when a matching email arrives, including sender, subject, and message details.",
    steps: ["Gmail trigger", "Filter message", "Send Slack alert"],
  },
  {
    title: "Lead Capture Automation",
    description:
      "Capture inbound leads, add them to Google Sheets, and trigger a personalized follow-up.",
    steps: ["Webhook trigger", "Create lead", "Append to Google Sheets"],
  },
  {
    title: "AI Email Summary",
    description:
      "Summarize long customer emails with AI and deliver concise action items to your team.",
    steps: ["Gmail trigger", "OpenAI summary", "Slack notification"],
  },
];

const plans = [
  {
    name: "Starter",
    price: "$19",
    description:
      "Perfect for solo founders and small businesses starting their automation journey.",
    badge: "",
    features: [
      "10 Active Workflows",
      "500 Automation Runs / Month",
      "Unlimited Webhooks",
      "Gmail, Slack & Google Sheets",
      "AI Workflow Actions",
      "Workflow Template Marketplace",
      "Email Support",
    ],
  },
  {
    name: "Pro",
    price: "$59",
    description:
      "Ideal for growing teams that need powerful automation at scale.",
    badge: "Most Popular",
    features: [
      "50 Active Workflows",
      "20,000 Automation Runs / Month",
      "Everything in Starter",
      "Premium Workflow Templates",
      "API Access",
      "Priority Support",
      "Advanced AI Automation",
    ],
  },
  {
    name: "Business",
    price: "$149",
    description:
      "Built for businesses that need team collaboration and higher automation limits.",
    badge: "",
    features: [
      "Unlimited Active Workflows",
      "100,000 Automation Runs / Month",
      "Everything in Pro",
      "Team Access",
      "Advanced Analytics",
      "API Access",
      "Dedicated Onboarding",
    ],
  },
];

const reliabilityItems = [
  "Multi-tenant workspace isolation",
  "Retry handling and dead-letter queue",
  "Workflow execution logs and analytics",
  "Role-based access controls",
  "Secure public webhook endpoints",
  "Production deployment on AWS infrastructure",
];

const businessBenefits = [
  {
    title: "Faster Setup",
    icon: "⚡",
    description:
      "Launch production-ready workflows in minutes with templates and a visual workflow builder.",
  },
  {
    title: "AI Built-In",
    icon: "🤖",
    description:
      "Use AI for summaries, classifications, content generation, and workflow automation.",
  },
  {
    title: "Enterprise Security",
    icon: "🔒",
    description:
      "HTTPS, encrypted credentials, tenant isolation, and role-based access control protect your data.",
  },
  {
    title: "Scale with Confidence",
    icon: "📈",
    description:
      "Start small and increase automation capacity as your business grows.",
  },
  {
    title: "Essential Integrations",
    icon: "🔗",
    description:
      "Connect Gmail, Slack, Google Sheets, OpenAI, webhooks, and more from one platform.",
  },
  {
    title: "Complete Visibility",
    icon: "📊",
    description:
      "Monitor workflow history, execution logs, retries, and automation health from one dashboard.",
  },
];

const faqs = [
  {
    question: "Do I need coding experience?",
    answer:
      "No. You can start from a ready-made template, configure the trigger and actions, test the workflow, and activate it from the dashboard.",
  },
  {
    question: "Which integrations are included?",
    answer:
      "Version 1.0 includes Gmail, Slack, Google Sheets, OpenAI, webhooks, scheduled workflows, HTTP requests, leads, conditions, and wait actions.",
  },
  {
    question: "Can I test a workflow before activating it?",
    answer:
      "Yes. You can run workflows manually, test webhook-based automations, review execution logs, and fix configuration issues before activation.",
  },
  {
    question: "How are failed workflow runs handled?",
    answer:
      "Failed runs include execution logs, retry handling, error details, and dead-letter tracking so you can diagnose and recover automations safely.",
  },
  {
    question: "Is my integration data secure?",
    answer:
      "OAuth tokens and integration credentials are encrypted, tenant data is isolated, API keys are stored as hashes, and public traffic is protected with HTTPS and production security controls.",
  },
  {
    question: "Can I cancel or change my plan?",
    answer:
      "You can manage your subscription from the billing dashboard. Plan capacity and workflow limits are shown clearly before you upgrade.",
  },
];


const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://app.neuralshielddigital.com/#organization",
      name: "NeuralShieldDigital",
      url: "https://app.neuralshielddigital.com",
      description:
        "NeuralShieldDigital provides an AI-powered workflow automation platform for businesses, agencies, consultants, and SaaS teams.",
      contactPoint: [
        {
          "@type": "ContactPoint",
          contactType: "customer support",
          email: "support@neuralshielddigital.com",
          availableLanguage: ["English"],
        },
        {
          "@type": "ContactPoint",
          contactType: "sales",
          email: "sales@neuralshielddigital.com",
          availableLanguage: ["English"],
        },
      ],
    },
    {
      "@type": "WebSite",
      "@id": "https://app.neuralshielddigital.com/#website",
      url: "https://app.neuralshielddigital.com",
      name: "NeuralShieldDigital",
      publisher: {
        "@id": "https://app.neuralshielddigital.com/#organization",
      },
      inLanguage: "en-US",
    },
    {
      "@type": "SoftwareApplication",
      "@id": "https://app.neuralshielddigital.com/#software",
      name: "NeuralShieldDigital Automation Platform",
      url: "https://app.neuralshielddigital.com",
      applicationCategory: "BusinessApplication",
      applicationSubCategory: "Workflow Automation Software",
      operatingSystem: "Web",
      description:
        "Build and automate business workflows using Gmail, Slack, Google Sheets, webhooks, schedules, HTTP requests, and AI-powered actions.",
      featureList: [
        "Visual workflow builder",
        "Gmail automation",
        "Slack automation",
        "Google Sheets automation",
        "OpenAI workflow actions",
        "Webhook triggers and actions",
        "Scheduled workflows",
        "Conditions and wait actions",
        "Execution logs and retries",
        "Workflow templates",
      ],
      provider: {
        "@id": "https://app.neuralshielddigital.com/#organization",
      },
      offers: {
        "@type": "AggregateOffer",
        priceCurrency: "USD",
        lowPrice: "19",
        highPrice: "149",
        offerCount: "3",
        url: "https://app.neuralshielddigital.com/#pricing",
      },
    },
    {
      "@type": "FAQPage",
      "@id": "https://app.neuralshielddigital.com/#faq",
      mainEntity: faqs.map((faq) => ({
        "@type": "Question",
        name: faq.question,
        acceptedAnswer: {
          "@type": "Answer",
          text: faq.answer,
        },
      })),
    },
  ],
};

const structuredDataJson = JSON.stringify(structuredData).replace(
  /</g,
  "\\u003c",
);

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#f7f5ee] text-[#17241f]">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: structuredDataJson }}
      />
      <header className="sticky top-0 z-50 border-b border-black/10 bg-[#f7f5ee]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0f6b57] text-sm font-bold text-white">
              NS
            </div>

            <div>
              <p className="text-sm font-bold tracking-tight">
                NeuralShieldDigital
              </p>
              <p className="text-xs text-black/55">
                AI Automation Platform
              </p>
            </div>
          </Link>

          <nav className="hidden items-center gap-7 text-sm font-medium md:flex">
            <a className="hover:text-[#0f6b57]" href="#features">
              Features
            </a>
            <a className="hover:text-[#0f6b57]" href="#integrations">
              Integrations
            </a>
            <a className="hover:text-[#0f6b57]" href="#pricing">
              Pricing
            </a>
            <a className="hover:text-[#0f6b57]" href="#security">
              Reliability
            </a>
            <a className="hover:text-[#0f6b57]" href="#faq">
              FAQ
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="rounded-xl border border-black/15 bg-white px-4 py-2.5 text-sm font-semibold transition hover:border-[#0f6b57]/40"
            >
              Sign in
            </Link>

            <Link
              href="/signup"
              className="rounded-xl bg-[#0f6b57] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0b5747]"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <section className="relative overflow-hidden border-b border-black/10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(15,107,87,0.12),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(15,107,87,0.08),transparent_32%)]" />

        <div className="relative mx-auto grid max-w-7xl gap-14 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-28">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#0f6b57]/20 bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
              ✨ AI-Powered Workflow Automation Platform
            </div>

            <h1 className="mt-6 max-w-4xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              Automate Your Business Operations with AI — Without Writing Code.
            </h1>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-black/65">
              Connect Gmail, Slack, Google Sheets, Webhooks, and AI to automate repetitive work, eliminate manual processes, and scale your business from one secure platform. Build reliable workflows in minutes—not weeks.

            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/signup"
                className="rounded-xl bg-[#0f6b57] px-6 py-3.5 text-center text-sm font-bold text-white transition hover:bg-[#0b5747]"
              >
                Start Building
              </Link>

              <Link
                href="#pricing"
                className="rounded-xl border border-black/15 bg-white px-6 py-3.5 text-center text-sm font-bold transition hover:border-[#0f6b57]/40"
              >
                Explore Templates
              </Link>
            </div>

            <div className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-sm text-black/60">
              <span>✓ No coding required</span>
              <span>✓ Secure AWS Infrastructure</span>
              <span>✓ AI-Powered Workflows</span>
              <span>✓ Multi-Tenant Security</span>
            </div>
          </div>

          <div className="rounded-3xl border border-black/10 bg-white p-5 shadow-2xl shadow-black/10 sm:p-7">
            <div className="flex items-center justify-between border-b border-black/10 pb-5">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#0f6b57]">
                  Workflow Builder
                </p>
                <p className="mt-2 text-xl font-bold">
                  AI Sales Reply to Slack
                </p>
              </div>

              <span className="rounded-full bg-[#e4f4ec] px-3 py-1 text-xs font-bold text-[#0f6b57]">
                Active
              </span>
            </div>

            <div className="mt-6 grid gap-4">
              <div className="rounded-2xl border border-[#0f6b57]/20 bg-[#f2faf6] p-5">
                <p className="text-xs font-bold uppercase text-[#0f6b57]">
                  Trigger
                </p>
                <p className="mt-2 font-bold">Webhook received</p>
                <p className="mt-2 text-sm text-black/55">
                  Receive lead name, email, and message data.
                </p>
              </div>

              <div className="mx-auto h-8 w-px bg-black/15" />

              <div className="rounded-2xl border border-black/10 bg-white p-5">
                <p className="text-xs font-bold uppercase text-[#0f6b57]">
                  Action 1
                </p>
                <p className="mt-2 font-bold">OpenAI text generate</p>
                <p className="mt-2 text-sm text-black/55">
                  Create a professional, personalized sales response.
                </p>
              </div>

              <div className="mx-auto h-8 w-px bg-black/15" />

              <div className="rounded-2xl border border-black/10 bg-white p-5">
                <p className="text-xs font-bold uppercase text-[#0f6b57]">
                  Action 2
                </p>
                <p className="mt-2 font-bold">Send Slack message</p>
                <p className="mt-2 text-sm text-black/55">
                  Deliver the generated response to your sales team.
                </p>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-3 gap-3">
              {[
                ["99.9%", "Platform Availability"],
                ["Secure AWS Hosted"],
                ["AI Automation Ready"],
              ].map(([value, label]) => (
                <div
                  key={label}
                  className="rounded-xl bg-[#f7f5ee] px-3 py-4 text-center"
                >
                  <p className="font-bold">{value}</p>
                  <p className="mt-1 text-xs text-black/50">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

<section className="bg-white">
  <div className="mx-auto max-w-7xl px-5 py-24 sm:px-8">
    <div className="mx-auto max-w-3xl text-center">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
        Product Showcase
      </p>

      <h2 className="mt-4 text-4xl font-bold tracking-tight">
        See NeuralShieldDigital in Action
      </h2>

      <p className="mt-6 text-lg text-black/60">
        Build, monitor, and scale your automations from one secure
        workspace with visual workflows, AI actions, usage analytics,
        and built-in integrations.
      </p>
    </div>

    <div className="mt-16 overflow-hidden rounded-3xl border border-black/10 bg-[#f8faf9] p-2 shadow-2xl">
      <Image
        src="/images/dashboard-preview.png"
        alt="NeuralShieldDigital automation dashboard"
        width={1600}
        height={900}
        className="h-auto w-full rounded-2xl"
      />
    </div>

    <div className="mt-10 grid gap-6 md:grid-cols-3">
      {[
        {
          title: "Visual Dashboard",
          description:
            "Monitor workflow usage, execution health, onboarding progress, and subscription capacity.",
        },
        {
          title: "Workflow Automation",
          description:
            "Build automations using Gmail, Slack, webhooks, Google Sheets, AI, and business actions.",
        },
        {
          title: "Usage Analytics",
          description:
            "Track workflow executions, plan limits, billing usage, and automation performance.",
        },
      ].map((item) => (
        <article
          key={item.title}
          className="rounded-2xl border border-black/10 bg-white p-6 shadow-sm"
        >
          <h3 className="font-bold">{item.title}</h3>
          <p className="mt-3 text-sm leading-7 text-black/60">
            {item.description}
          </p>
        </article>
      ))}
    </div>

    <div className="mt-24 grid items-center gap-12 lg:grid-cols-[0.85fr_1.15fr]">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
          Visual Workflow Builder
        </p>

        <h3 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
          Build powerful automations without writing code.
        </h3>

        <p className="mt-5 text-base leading-7 text-black/60">
          Combine triggers, actions, AI, integrations, and business logic
          in one visual workspace. Test workflows before activation and
          monitor every execution from your dashboard.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {[
            "Webhook and scheduled triggers",
            "Conditional workflow branches",
            "OpenAI-powered actions",
            "Gmail, Slack, and Google Sheets",
            "Execution testing and validation",
            "Secure integration credentials",
          ].map((item) => (
            <div
              key={item}
              className="flex items-start gap-3 rounded-xl border border-black/10 bg-white p-4"
            >
              <span className="mt-0.5 text-[#0f6b57]">✓</span>
              <span className="text-sm font-semibold text-black/75">
                {item}
              </span>
            </div>
          ))}
        </div>

        <Link
          href="/signup"
          className="mt-8 inline-flex rounded-xl bg-[#0f6b57] px-6 py-3 font-bold text-white transition hover:bg-[#0b5747]"
        >
          Build Your First Workflow
        </Link>
      </div>

      <div className="overflow-hidden rounded-3xl border border-black/10 bg-[#f8faf9] p-2 shadow-2xl">
        <Image
          src="/images/workflow-builder-preview.png"
          alt="NeuralShieldDigital visual workflow builder"
          width={1536}
          height={1024}
          className="h-auto w-full rounded-2xl"
        />
      </div>
    </div>
  </div>
</section>

<section className="bg-white">
  <div className="mx-auto max-w-7xl px-5 py-24 sm:px-8">

    <div className="mx-auto max-w-3xl text-center">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
        Product Showcase
      </p>

      <h2 className="mt-4 text-4xl font-bold tracking-tight">
        See NeuralShieldDigital in Action
      </h2>

      <p className="mt-6 text-lg text-black/60">
        Build, monitor, and scale your automations from one secure
        workspace with visual workflows, AI actions, usage analytics,
        and built-in integrations.
      </p>
    </div>

    {/* Dashboard */}

    <div className="mt-16 overflow-hidden rounded-3xl border border-black/10 bg-[#f8faf9] shadow-2xl">

      <img
        src="/images/dashboard-preview.png"
        alt="NeuralShieldDigital Dashboard"
        className="w-full"
      />

    </div>

    <div className="mt-10 grid gap-6 md:grid-cols-3">

      <div className="rounded-2xl border border-black/10 p-6">
        <h3 className="font-bold">Visual Dashboard</h3>

        <p className="mt-3 text-sm text-black/60">
          Monitor workflow usage, execution health,
          onboarding progress, and subscriptions.
        </p>
      </div>

      <div className="rounded-2xl border border-black/10 p-6">
        <h3 className="font-bold">Workflow Automation</h3>

        <p className="mt-3 text-sm text-black/60">
          Build automations using Gmail,
          Slack, Webhooks, Google Sheets,
          AI, and custom actions.
        </p>
      </div>

      <div className="rounded-2xl border border-black/10 p-6">
        <h3 className="font-bold">Usage Analytics</h3>

        <p className="mt-3 text-sm text-black/60">
          Track workflow executions,
          plan limits, billing,
          and automation performance.
        </p>
      </div>

    </div>

  </div>
</section>

<section className="border-y border-black/10 bg-[#f7f8f4]">
  <div className="mx-auto max-w-7xl px-5 py-24 sm:px-8">
    <div className="mx-auto max-w-3xl text-center">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
        How It Works
      </p>

      <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
        From repetitive task to reliable automation in three steps.
      </h2>

      <p className="mt-5 text-base leading-7 text-black/60">
        Choose how your workflow starts, connect the actions your business
        needs, then activate and monitor every execution from one workspace.
      </p>
    </div>

    <div className="relative mt-14 grid gap-6 lg:grid-cols-3">
      {[
        {
          number: "01",
          title: "Choose a Trigger",
          description:
            "Start with Gmail, Slack, a webhook, a schedule, a new lead, or another supported business event.",
        },
        {
          number: "02",
          title: "Build Your Workflow",
          description:
            "Add conditions, AI actions, Google Sheets, notifications, lead actions, and secure integrations.",
        },
        {
          number: "03",
          title: "Activate and Monitor",
          description:
            "Test your automation, activate it when ready, and track executions, usage, retries, and results.",
        },
      ].map((step) => (
        <article
          key={step.number}
          className="relative rounded-3xl border border-black/10 bg-white p-8 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
        >
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[#e1f1eb] text-sm font-bold text-[#0f6b57]">
            {step.number}
          </div>

          <h3 className="mt-6 text-xl font-bold">{step.title}</h3>

          <p className="mt-4 text-sm leading-7 text-black/60">
            {step.description}
          </p>
        </article>
      ))}
    </div>

    <div className="mt-12 text-center">
      <Link
        href="/signup"
        className="inline-flex rounded-xl bg-[#0f6b57] px-7 py-3.5 font-bold text-white transition hover:bg-[#0b5747]"
      >
        Start Building Free
      </Link>
    </div>
  </div>
</section>

<section className="bg-[#f3f8f5] border-y border-black/10">
  <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8">

    <div className="mx-auto max-w-3xl text-center">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
        Why Businesses Choose NeuralShieldDigital
      </p>

      <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
        Built for reliable automation, not unnecessary complexity.
      </h2>

      <p className="mt-5 text-base leading-7 text-black/60">
        Automate repetitive work, integrate your existing tools, and
        scale confidently using one secure workflow automation platform.
      </p>
    </div>

    <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
      {businessBenefits.map((item) => (
        <article
          key={item.title}
          className="rounded-2xl border border-black/10 bg-white p-7 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
        >
          <div className="text-3xl">{item.icon}</div>

          <h3 className="mt-5 text-xl font-bold">
            {item.title}
          </h3>

          <p className="mt-4 text-sm leading-7 text-black/60">
            {item.description}
          </p>
        </article>
      ))}
    </div>

    <div className="mt-14 rounded-3xl bg-[#0f6b57] px-8 py-10 text-center text-white">

      <div className="flex flex-wrap justify-center gap-6 text-sm font-semibold">

        <span>✓ Built for Growing Businesses</span>

        <span>✓ Secure AWS Infrastructure</span>

        <span>✓ AI-Powered Automation</span>

        <span>✓ Transparent Pricing</span>

        <span>✓ Multi-Tenant Security</span>

      </div>

      <h3 className="mt-8 text-3xl font-bold">
        Ready to automate your first workflow?
      </h3>

      <p className="mt-4 text-white/80">
        Join businesses using AI-powered workflow automation to save
        time and eliminate repetitive work.
      </p>

      <Link
        href="/signup"
        className="mt-8 inline-flex rounded-xl bg-white px-7 py-3.5 font-bold text-[#0f6b57] transition hover:bg-[#f3f3f3]"
      >
        Start Building
      </Link>

    </div>

  </div>
</section>

      <section id="features" className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
        <div className="max-w-3xl">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
            Production automation
          </p>

          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Everything required to move from idea to reliable automation.
          </h2>

          <p className="mt-4 text-base leading-7 text-black/60">
            Create multi-step workflows, add AI, branch with conditions,
            inspect run logs, retry failures, and monitor monthly usage.
          </p>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {[
            {
              title: "Visual Workflow Builder",
              text: "Create and reorder multiple actions with configuration-aware editing.",
            },
            {
              title: "Conditions and Branching",
              text: "Build true and false execution paths for dynamic workflow logic.",
            },
            {
              title: "Templates and Quick Start",
              text: "Launch from proven workflow patterns instead of starting from zero.",
            },
            {
              title: "Execution Reliability",
              text: "Review logs, retry failures, and track dead-letter workflow runs.",
            },
          ].map((feature) => (
            <article
              key={feature.title}
              className="rounded-2xl border border-black/10 bg-white p-6 shadow-sm"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e4f4ec] font-bold text-[#0f6b57]">
                ✓
              </div>

              <h3 className="mt-5 text-lg font-bold">{feature.title}</h3>

              <p className="mt-3 text-sm leading-6 text-black/60">
                {feature.text}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section
        id="integrations"
        className="border-y border-black/10 bg-white"
      >
        <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
          <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
                Core integrations
              </p>

              <h2 className="mt-3 text-3xl font-bold tracking-tight">
                Connect the tools your team already uses.
              </h2>

              <p className="mt-4 text-base leading-7 text-black/60">
                The MVP integration catalog is intentionally focused on
                high-value business workflows instead of an oversized,
                difficult-to-maintain catalog.
              </p>

              <Link
                href="/signup"
                className="mt-6 inline-block rounded-xl bg-[#0f6b57] px-5 py-3 text-sm font-bold text-white"
              >
                Connect your workspace
              </Link>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {integrations.map((integration) => (
                <article
                  key={integration.name}
                  className="rounded-2xl border border-black/10 bg-[#faf9f5] p-6"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-lg font-bold text-[#0f6b57] shadow-sm">
                    {integration.name.slice(0, 1)}
                  </div>

                  <h3 className="mt-5 text-lg font-bold">
                    {integration.name}
                  </h3>

                  <p className="mt-2 text-sm leading-6 text-black/60">
                    {integration.description}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
        <div className="text-center">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
            Workflow examples
          </p>

          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Start with automations that create immediate business value.
          </h2>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {automationExamples.map((example) => (
            <article
              key={example.title}
              className="rounded-2xl border border-black/10 bg-white p-6 shadow-sm"
            >
              <h3 className="text-xl font-bold">{example.title}</h3>

              <p className="mt-3 text-sm leading-6 text-black/60">
                {example.description}
              </p>

              <ol className="mt-6 grid gap-3">
                {example.steps.map((step, index) => (
                  <li
                    key={step}
                    className="flex items-center gap-3 rounded-xl bg-[#f7f5ee] px-4 py-3 text-sm font-medium"
                  >
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#0f6b57] text-xs font-bold text-white">
                      {index + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </article>
          ))}
        </div>
      </section>

      <section id="security" className="bg-[#10251e] text-white">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#8ed5b8]">
              Reliability and control
            </p>

            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Built for real business operations, not just demos.
            </h2>

            <p className="mt-5 text-base leading-7 text-white/65">
              Workflows include tenant isolation, execution history, retries,
              quota enforcement, authentication, and production deployment
              controls.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {reliabilityItems.map((item) => (
              <div
                key={item}
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-white/80"
              >
                <span className="mr-2 font-bold text-[#8ed5b8]">✓</span>
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
        <div className="text-center">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
            Simple pricing
          </p>

          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Start small and upgrade as automation volume grows.
          </h2>

          <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-black/60">
            Prices are shown in USD. Checkout is completed securely through
            Paddle.
          </p>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {plans.map((plan) => (
            <article
              key={plan.name}
              className={`relative flex flex-col rounded-3xl border bg-white p-7 ${
                plan.badge
                  ? "border-[#0f6b57] shadow-xl shadow-[#0f6b57]/10"
                  : "border-black/10"
              }`}
            >
              {plan.badge ? (
                <span className="absolute right-6 top-6 rounded-full bg-[#0f6b57] px-3 py-1 text-xs font-bold text-white">
                  {plan.badge}
                </span>
              ) : null}

              <h3 className="text-xl font-bold">{plan.name}</h3>

              <p className="mt-3 min-h-12 text-sm leading-6 text-black/55">
                {plan.description}
              </p>

              <div className="mt-6 flex items-end gap-2">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="pb-1 text-sm text-black/55">
                  USD / month
                </span>
              </div>

              <ul className="mt-6 grid flex-1 gap-3">
                {plan.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex gap-3 text-sm text-black/65"
                  >
                    <span className="font-bold text-[#0f6b57]">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>

              <Link
                href="/signup"
                className={`mt-7 rounded-xl px-5 py-3 text-center text-sm font-bold ${
                  plan.badge
                    ? "bg-[#0f6b57] text-white"
                    : "border border-black/15 bg-white"
                }`}
              >
                Get Started
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section
        id="faq"
        className="border-t border-black/10 bg-[#f1efe7]"
      >
        <div className="mx-auto max-w-5xl px-5 py-20 sm:px-8">
          <div className="text-center">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
              Frequently asked questions
            </p>

            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to start automating confidently.
            </h2>

            <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-black/60">
              Clear answers about setup, integrations, reliability, security,
              and billing.
            </p>
          </div>

          <div className="mt-10 grid gap-4">
            {faqs.map((faq) => (
              <details
                key={faq.question}
                className="group rounded-2xl border border-black/10 bg-white p-5"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-bold">
                  <span>{faq.question}</span>

                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#e4f4ec] text-lg text-[#0f6b57] transition group-open:rotate-45">
                    +
                  </span>
                </summary>

                <p className="mt-4 max-w-3xl text-sm leading-7 text-black/60">
                  {faq.answer}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-black/10 bg-white">
        <div className="mx-auto max-w-5xl px-5 py-20 text-center sm:px-8">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#0f6b57]">
            Start automating
          </p>

          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
            Turn repetitive work into reliable workflows.
          </h2>

          <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-black/60">
            Create your workspace, connect your apps, launch a template, and
            activate your first production workflow.
          </p>

          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              href="/signup"
              className="rounded-xl bg-[#0f6b57] px-7 py-3.5 text-sm font-bold text-white"
            >
              Get Started
            </Link>

            <Link
              href="/login"
              className="rounded-xl border border-black/15 px-7 py-3.5 text-sm font-bold"
            >
              Sign in
            </Link>
          </div>

          <p className="mt-5 text-sm text-black/50">
            Secure checkout. Upgrade anytime as your automation needs grow.
          </p>
        </div>
      </section>

<section className="bg-white">
  <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
    <div className="overflow-hidden rounded-[2rem] bg-[#0f5f4e] px-6 py-14 text-center text-white shadow-2xl sm:px-12 lg:py-16">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/70">
        Start Automating Today
      </p>

      <h2 className="mx-auto mt-4 max-w-3xl text-3xl font-bold tracking-tight sm:text-5xl">
        Turn repetitive business work into reliable automated workflows.
      </h2>

      <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-white/75">
        Connect your tools, launch AI-powered automations, and manage
        workflow activity from one secure platform.
      </p>

      <div className="mt-9 flex flex-col justify-center gap-4 sm:flex-row">
        <Link
          href="/signup"
          className="inline-flex items-center justify-center rounded-xl bg-white px-7 py-3.5 font-bold text-[#0f5f4e] transition hover:bg-[#f1f3ef]"
        >
          Start Building Free
        </Link>

        <Link
          href="/contact"
          className="inline-flex items-center justify-center rounded-xl border border-white/35 px-7 py-3.5 font-bold text-white transition hover:bg-white/10"
        >
          Contact Sales
        </Link>
      </div>

      <div className="mt-9 flex flex-wrap justify-center gap-x-7 gap-y-3 text-sm text-white/70">
        <span>✓ No coding required</span>
        <span>✓ Secure cloud infrastructure</span>
        <span>✓ AI-powered actions</span>
        <span>✓ Cancel anytime</span>
      </div>
    </div>
  </div>
</section>

      <footer className="border-t border-black/10 bg-[#f7f5ee]">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-8 text-sm text-black/55 sm:px-8 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-bold text-[#17241f]">
              NeuralShieldDigital
            </p>
            <p className="mt-1">
              AI automation for growing businesses.
            </p>
          </div>

          <div className="flex flex-wrap gap-5">
            <Link href="/login" className="hover:text-[#0f6b57]">
              Sign in
            </Link>
            <Link href="/signup" className="hover:text-[#0f6b57]">
              Get Started
            </Link>
            <a href="#pricing" className="hover:text-[#0f6b57]">
              Pricing
            </a>
            <Link href="/privacy" className="hover:text-[#0f6b57]">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-[#0f6b57]">
              Terms
            </Link>
            <Link href="/contact" className="hover:text-[#0f6b57]">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
