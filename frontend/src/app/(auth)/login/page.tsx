import Link from "next/link";

import { LoginForm } from "@/features/auth/components/LoginForm";

export const metadata = { title: "Sign in · Tradinghub" };

export default function LoginPage() {
  return (
    <div className="rise [animation-delay:80ms]">
      <h1 className="font-display text-[2.75rem] leading-[1.05] tracking-tight">
        Welcome back.
      </h1>
      <p className="mt-3 text-sm text-ink-dim">
        Pick up where the last trade left off.
      </p>

      <div className="mt-10">
        <LoginForm />
      </div>

      <p className="mt-8 border-t border-rule pt-6 text-xs text-ink-faint">
        New here?{" "}
        <Link
          href="/register"
          className="text-ink underline decoration-rule-strong underline-offset-4 transition-colors hover:text-accent hover:decoration-accent"
        >
          Create an account
        </Link>
      </p>
    </div>
  );
}
