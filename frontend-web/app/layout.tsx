import type { Metadata } from "next";
import "./globals.css";

const SITE_URL = "https://app.neuralshielddigital.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),

  title: {
    default: "NeuralShieldDigital | AI Automation Platform",
    template: "%s | NeuralShieldDigital",
  },

  description:
    "Build, connect, and automate business workflows with Gmail, Slack, Google Sheets, webhooks, scheduled workflows, and AI.",

  applicationName: "NeuralShieldDigital",

  keywords: [
    "AI automation platform",
    "workflow automation",
    "business automation",
    "Zapier alternative",
    "Make alternative",
    "no-code automation",
    "Gmail automation",
    "Slack automation",
    "Google Sheets automation",
    "webhook automation",
    "scheduled workflows",
    "AI workflow automation",
  ],

  authors: [
    {
      name: "NeuralShieldDigital",
      url: SITE_URL,
    },
  ],

  creator: "NeuralShieldDigital",
  publisher: "NeuralShieldDigital",
  category: "Technology",

  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: "NeuralShieldDigital",
    title: "NeuralShieldDigital | AI Automation Platform",
    description:
      "Build, connect, and automate business workflows with Gmail, Slack, Google Sheets, webhooks, scheduled workflows, and AI.",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "NeuralShieldDigital AI Automation Platform",
      },
    ],
  },

  twitter: {
    card: "summary_large_image",
    title: "NeuralShieldDigital | AI Automation Platform",
    description:
      "Build, connect, and automate business workflows with Gmail, Slack, Google Sheets, webhooks, scheduled workflows, and AI.",
    images: ["/twitter-image"],
  },

  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
