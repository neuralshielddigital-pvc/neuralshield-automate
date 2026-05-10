import Link from "next/link";

type AuthCardProps = {
  title: string;
  subtitle: string;
  footerText: string;
  footerHref: string;
  footerCta: string;
  children: React.ReactNode;
};

export function AuthCard({ title, subtitle, footerText, footerHref, footerCta, children }: AuthCardProps) {
  return (
    <main className="auth-page">
      <section className="auth-card p-7 sm:p-8">
        <div className="mb-8">
          <div className="brand-mark mb-5 h-12 w-12 ring-4 ring-mint/70">
            NS
          </div>
          <p className="page-kicker mb-2">NeuralShieldDigital</p>
          <h1 className="text-2xl font-semibold text-ink sm:text-3xl">{title}</h1>
          <p className="mt-2 text-sm leading-6 text-steel">{subtitle}</p>
        </div>
        {children}
        <p className="mt-6 rounded-lg border border-line bg-linen/70 px-4 py-3 text-sm text-steel">
          {footerText}{" "}
          <Link className="font-semibold text-pine hover:text-slatepanel hover:underline" href={footerHref}>
            {footerCta}
          </Link>
        </p>
      </section>
    </main>
  );
}
