import Link from "next/link";

import { RegisterForm } from "@/features/auth/components/RegisterForm";

export const metadata = { title: "Register · Tradinghub" };

export default function RegisterPage() {
  return (
    <div className="rise [animation-delay:80ms]">
      <h1 className="font-display text-[2.5rem] leading-[1.05] font-semibold tracking-tight">
        Create your account
      </h1>
      <p className="mt-3 text-sm text-ink-dim">
        Takes a few seconds. An email and a password, nothing else.
      </p>

      <div className="mt-10">
        <RegisterForm />
      </div>

      <p className="mt-8 text-sm text-ink-dim">
        Already have an account?{" "}
        <Link
          href="/login"
          className="font-medium text-ink underline decoration-accent underline-offset-4 transition-colors hover:text-accent"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
