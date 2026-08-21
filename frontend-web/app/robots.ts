import type { MetadataRoute } from "next";

const SITE_URL = "https://app.neuralshielddigital.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: [
          "/",
          "/contact",
          "/privacy",
          "/terms",
        ],
        disallow: [
          "/admin",
          "/admin/",
          "/dashboard",
          "/dashboard/",
          "/api",
          "/api/",
          "/forgot-password",
          "/lead-form",
          "/login",
          "/resend-verification",
          "/reset-password",
          "/signup",
          "/verify-email",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
