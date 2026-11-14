import Link from "next/link";

import { LoginForm } from "@/features/auth/components/LoginForm";

export const metadata = { title: "Sign in · Tradinghub" };

export default function LoginPage() {
  return (
    <div className="rise [animation-delay:80ms]">
      <h1 className="font-display text-[2.5rem] leading-[1.05] font-semibold tracking-tight">
        Welcome back.
      </h1>
      <p className="mt-3 text-sm text-ink-dim">
        Pick up where the last trade left off.
      </p>

      <div className="mt-10">
        <LoginForm />
      </div>

      <p className="mt-8 text-sm text-ink-dim">
        New here?{" "}
        <Link
          href="/register"
          className="font-medium text-ink underline decoration-accent underline-offset-4 transition-colors hover:text-accent"
        >
          Create an account
        </Link>
      </p>
    </div>
  );
}
