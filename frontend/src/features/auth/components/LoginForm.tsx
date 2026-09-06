"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
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
    mode: "onTouched",
  });

  const submit = handleSubmit((values) => {
    loginMutation.mutate(values, {
      onSuccess: () => router.push("/dashboard"),
    });
  });

  return (
    <form onSubmit={submit} noValidate className="space-y-7">
      <Field
        id="email"
        label="Email"
        type="email"
        autoComplete="email"
        autoFocus
        error={errors.email?.message}
        {...field("email")}
      />

      <Field
        id="password"
        label="Password"
        type="password"
        autoComplete="current-password"
        error={errors.password?.message}
        {...field("password")}
      />

      {/* The server answers a wrong password and an unknown email identically. One message for
          both, deliberately: do not try to be more specific here. */}
      {loginMutation.error && (
        <p
          role="alert"
          className="border-l-2 border-danger bg-danger/5 py-2 pl-3 text-sm text-danger"
        >
          {messageFor(loginMutation.error)}
        </p>
      )}

      <Button type="submit" disabled={loginMutation.isPending}>
        {loginMutation.isPending ? "Signing in" : "Sign in"}
      </Button>
    </form>
  );
}
