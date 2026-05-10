"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearTokens, getAccessToken } from "@/lib/token-storage";
import { getMe } from "@/lib/auth";
import type { CurrentUserResponse } from "@/lib/types";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "D" },
  { href: "/dashboard/campaigns", label: "Campaigns", icon: "C" },
  { href: "/dashboard/leads", label: "Leads", icon: "L" },
  { href: "/dashboard/workflows", label: "Workflows", icon: "W" },
  { href: "/dashboard/billing", label: "Billing", icon: "B" },
  { href: "/dashboard/affiliate", label: "Affiliate", icon: "A" }
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<CurrentUserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    let active = true;
    const token = getAccessToken();
    if (!token) {
      setRedirecting(true);
      setLoading(false);
      router.replace("/login");
      return () => {
        active = false;
      };
    }

    getMe()
      .then((response) => {
        if (active) {
          setSession(response);
        }
      })
      .catch(() => {
        if (!active) {
          return;
        }
        clearTokens();
        setRedirecting(true);
        router.replace("/login");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [router]);

  function handleLogout() {
    clearTokens();
    router.replace("/login");
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4 text-sm font-medium text-steel">
        <div className="surface-card flex items-center gap-3 px-5 py-4">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-pine" />
          Loading dashboard...
        </div>
      </main>
    );
  }

  if (!session || redirecting) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4 text-sm font-medium text-steel">
        <div className="surface-card flex items-center gap-3 px-5 py-4">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-pine" />
          Redirecting to login...
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard-shell">
      <aside className="dashboard-sidebar hidden p-5 md:flex">
        <div className="flex items-center gap-3 border-b border-line pb-5">
          <div className="brand-mark h-11 w-11 ring-4 ring-mint/70">
            NS
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-ink">NeuralShieldDigital</p>
            <p className="truncate text-xs text-steel">{session.tenant.name}</p>
          </div>
        </div>

        <nav className="mt-5 grid gap-1.5">
          {[
            ...navItems,
            ...(session.user.role === "ADMIN" || session.user.role === "SUPER_ADMIN"
              ? [{ href: "/admin", label: "Admin", icon: "S" }]
              : [])
          ].map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                className={`sidebar-link ${
                  active ? "sidebar-link-active" : "sidebar-link-idle"
                }`}
                href={item.href}
                key={item.href}
              >
                <span className="sidebar-icon">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto rounded-2xl border border-line bg-linen/80 p-4">
          <p className="text-xs font-bold uppercase text-pine">Workspace</p>
          <p className="mt-1 truncate text-sm font-semibold text-ink">{session.user.role}</p>
        </div>
      </aside>

      <header className="dashboard-topbar">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="brand-mark h-10 w-10 text-xs ring-4 ring-mint/70 md:hidden">
              NS
            </div>
            <div>
              <p className="text-sm font-bold text-ink sm:text-base">Workspace console</p>
              <p className="text-xs text-steel">{session.tenant.name}</p>
            </div>
          </div>
          <div className="flex min-w-0 items-center gap-3">
            <span className="hidden max-w-[260px] truncate rounded-full border border-line bg-linen px-3 py-1.5 text-sm text-steel sm:inline">
              {session?.user.email}
            </span>
            <button
              className="btn-secondary px-3 py-2"
              onClick={handleLogout}
              type="button"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="dashboard-content">
        <div className="mx-auto max-w-6xl">
          <aside className="dashboard-sidebar mb-5 p-3 md:hidden">
            <nav className="flex gap-2 overflow-x-auto pb-1">
            {[
              ...navItems,
              ...(session.user.role === "ADMIN" || session.user.role === "SUPER_ADMIN"
                ? [{ href: "/admin", label: "Admin", icon: "S" }]
                : [])
            ].map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  className={`sidebar-link ${
                    active ? "sidebar-link-active" : "sidebar-link-idle"
                  }`}
                  href={item.href}
                  key={item.href}
                >
                  <span className="sidebar-icon">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
            </nav>
          </aside>
          <section className="min-w-0">{children}</section>
        </div>
      </div>
    </main>
  );
}
