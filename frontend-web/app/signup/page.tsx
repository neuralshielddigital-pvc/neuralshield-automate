import { Suspense } from "react";
import { SignupForm } from "@/app/signup/signup-form";

export default function SignupPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center px-4 py-10 text-sm text-steel">
          <div className="surface-card flex items-center gap-3 px-5 py-4">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-pine" />
            Loading signup...
          </div>
        </main>
      }
    >
      <SignupForm />
    </Suspense>
  );
}
