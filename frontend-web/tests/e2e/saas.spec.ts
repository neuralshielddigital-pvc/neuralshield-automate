import { expect, Page, test } from "@playwright/test";

const apiBase = "http://127.0.0.1:8000";

async function mockSession(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("nsd_access_token", "test-access");
    window.localStorage.setItem("nsd_refresh_token", "test-refresh");
  });
  await page.route(`${apiBase}/api/auth/me`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        user: {
          id: "user_1",
          email: "admin@example.com",
          is_active: true,
          role: "ADMIN",
          tenant_id: "tenant_1",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        tenant: {
          id: "tenant_1",
          name: "NeuralShieldDigital",
          slug: "neuralshielddigital",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      })
    });
  });
}

test("login page submits credentials", async ({ page }) => {
  await page.route(`${apiBase}/api/auth/login`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "test-access",
        refresh_token: "test-refresh",
        token_type: "bearer",
        expires_in: 900,
        user: {
          id: "user_1",
          email: "admin@example.com",
          is_active: true,
          role: "ADMIN",
          tenant_id: "tenant_1",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        tenant: {
          id: "tenant_1",
          name: "NeuralShieldDigital",
          slug: "neuralshielddigital",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      })
    });
  });

  await page.goto("/login");
  await page.getByPlaceholder("Email").fill("admin@example.com");
  await page.getByPlaceholder("Password").fill("StrongPassword!123");
  await page.getByRole("button", { name: /login/i }).click();
  await expect(page).toHaveURL(/dashboard/);
});

test("billing page renders current plan", async ({ page }) => {
  await mockSession(page);
  await page.route(`${apiBase}/api/billing/subscription`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        subscription: {
          id: "sub_1",
          stripe_customer_id: "cus_1",
          stripe_subscription_id: "stripe_sub_1",
          status: "ACTIVE",
          current_period_start: null,
          current_period_end: null,
          cancel_at_period_end: false,
          plan: { id: "plan_1", name: "Pro", stripe_price_id: "price_1", price: "49.00", interval: "monthly" }
        }
      })
    });
  });
  await page.goto("/dashboard/billing");
  await expect(page.getByText("Pro")).toBeVisible();
  await expect(page.getByText("ACTIVE")).toBeVisible();
});

test("affiliate page renders referral link", async ({ page }) => {
  await mockSession(page);
  await page.route(`${apiBase}/api/affiliate/me`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        is_registered: true,
        affiliate: {
          id: "aff_1",
          user_id: "user_1",
          referral_code: "NSD123",
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        referral_link: "http://localhost:3000/signup?ref=NSD123"
      })
    });
  });
  await page.route(`${apiBase}/api/affiliate/stats`, async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ total_referrals: 1, pending_commissions: "0", approved_commissions: "0", paid_commissions: "0" }) });
  });
  await page.route(`${apiBase}/api/affiliate/referrals`, async (route) => route.fulfill({ contentType: "application/json", body: "[]" }));
  await page.route(`${apiBase}/api/affiliate/commissions`, async (route) => route.fulfill({ contentType: "application/json", body: "[]" }));

  await page.goto("/dashboard/affiliate");
  await expect(page.getByText("NSD123")).toBeVisible();
});

test("leads page renders lead list", async ({ page }) => {
  await mockSession(page);
  await page.route(`${apiBase}/api/leads**`, async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "lead_1",
            tenant_id: "tenant_1",
            user_id: "user_1",
            name: "Rahul",
            email: "rahul@example.com",
            phone: "9999999999",
            source: "website",
            stage: "NEW",
            notes: null,
            last_contacted_at: null,
            tags: ["public-form"],
            metadata: {},
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }
        ],
        pagination: { page: 1, page_size: 25, total: 1, total_pages: 1 }
      })
    });
  });

  await page.goto("/dashboard/leads");
  await expect(page.getByText("rahul@example.com").first()).toBeVisible();
});

test("workflow page can create workflow", async ({ page }) => {
  await mockSession(page);
  await page.route(`${apiBase}/api/workflows`, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          id: "workflow_1",
          tenant_id: "tenant_1",
          user_id: "user_1",
          name: "Capture lead",
          description: null,
          is_active: false,
          public_webhook_key: "public_key",
          definition: {},
          triggers: [],
          actions: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
      });
      return;
    }
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [], pagination: { page: 1, page_size: 25, total: 0, total_pages: 0 } }) });
  });
  await page.route(`${apiBase}/api/workflows/*/runs`, async (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ items: [], pagination: { page: 1, page_size: 25, total: 0, total_pages: 0 } }) }));

  await page.goto("/dashboard/workflows");
  await page.getByPlaceholder("Workflow name").fill("Capture lead");
  await page.getByRole("button", { name: /create workflow/i }).click();
  await expect(page.getByText("Workflow created.")).toBeVisible();
});

test("public lead form submits", async ({ page }) => {
  await page.route(`${apiBase}/api/public/leads`, async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ success: true, message: "Thanks. We received your request." }) });
  });

  await page.goto("/lead-form");
  await page.getByPlaceholder("Name").fill("Rahul");
  await page.getByPlaceholder("Email").fill("rahul@example.com");
  await page.getByPlaceholder("Phone").fill("9999999999");
  await page.getByPlaceholder("Message").fill("I need automation");
  await page.getByRole("button", { name: /submit request/i }).click();
  await expect(page.getByText("Thanks. We received your request.")).toBeVisible();
});
