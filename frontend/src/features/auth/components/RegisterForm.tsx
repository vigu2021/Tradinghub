"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { API_CODES, ApiError, messageFor } from "@/lib/api/errors";

import { useRegister } from "../hooks";
import {
  MIN_PASSWORD_LENGTH,
  type RegisterRequest,
  registerSchema,
} from "../types";

export function RegisterForm() {
  const router = useRouter();
  const registerMutation = useRegister();
  const {
    register: field,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterRequest>({
    resolver: zodResolver(registerSchema),
    mode: "onTouched",
  });

  const submit = handleSubmit((values) => {
    registerMutation.mutate(values, {
      onSuccess: () => router.push("/dashboard"),
    });
  });

  const emailTaken =
    registerMutation.error instanceof ApiError &&
    registerMutation.error.code === API_CODES.EMAIL_TAKEN;

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
        autoComplete="new-password"
        hint={`At least ${MIN_PASSWORD_LENGTH} characters`}
        error={errors.password?.message}
        {...field("password")}
      />

      {registerMutation.error && (
        <p
          role="alert"
          className="border-l-2 border-danger bg-danger/5 py-2 pl-3 text-sm text-danger"
        >
          {messageFor(registerMutation.error)}{" "}
          {emailTaken && (
            <Link
              href="/login"
              className="underline decoration-danger/40 underline-offset-4 hover:decoration-danger"
            >
              Sign in instead
            </Link>
          )}
        </p>
      )}

      <Button type="submit" disabled={registerMutation.isPending}>
        {registerMutation.isPending ? "Creating account" : "Create account"}
      </Button>
    </form>
  );
}
