"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { messageFor } from "@/lib/api/errors";

import { useLogin } from "../hooks";
import { type LoginRequest, loginSchema } from "../types";

export function LoginForm() {
  const router = useRouter();
  const loginMutation = useLogin();
  const {
    register: field,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginRequest>({
    resolver: zodResolver(loginSchema),
  });

  const submit = handleSubmit((values) => {
    loginMutation.mutate(values, {
      onSuccess: () => router.push("/dashboard"),
    });
  });

  return (
    <form onSubmit={submit} noValidate>
      <label htmlFor="email">Email</label>
      <input
        id="email"
        type="email"
        autoComplete="email"
        aria-invalid={Boolean(errors.email)}
        {...field("email")}
      />
      {errors.email && <p role="alert">{errors.email.message}</p>}

      <label htmlFor="password">Password</label>
      <input
        id="password"
        type="password"
        autoComplete="current-password"
        aria-invalid={Boolean(errors.password)}
        {...field("password")}
      />
      {errors.password && <p role="alert">{errors.password.message}</p>}

      {/* The server answers a wrong password and an unknown email identically. One message for
          both, deliberately: do not try to be more specific here. */}
      {loginMutation.error && (
        <p role="alert">{messageFor(loginMutation.error)}</p>
      )}

      <button type="submit" disabled={loginMutation.isPending}>
        {loginMutation.isPending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
