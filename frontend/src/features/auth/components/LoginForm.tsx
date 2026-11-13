"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Field } from "@/components/ui/Field";
import {
  API_CODES,
  type ApiError,
  isApiError,
  messageFor,
} from "@/lib/api/errors";

import { useLogin } from "../hooks";
import { MAX_EMAIL_LENGTH, MAX_PASSWORD_LENGTH } from "../types";

const loginSchema = z.object({
  email: z
    .email("Please enter a valid email.")
    .max(MAX_EMAIL_LENGTH, "That email is too long."),
  password: z
    .string()
    .min(1, "Enter your password.")
    .max(MAX_PASSWORD_LENGTH, "That password is too long."),
});

type LoginValues = z.infer<typeof loginSchema>;

const SECONDS_PER_MINUTE = 60;

export function LoginForm() {
  const router = useRouter();
  const loginMutation = useLogin();
  const [lockedOut, setLockedOut] = useState(false);
  const {
    register: field,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    mode: "onTouched",
  });

  const lockout = isApiError(loginMutation.error, API_CODES.RATE_LIMITED)
    ? loginMutation.error
    : null;

  const submit = handleSubmit((values) => {
    loginMutation.mutate(values, {
      onSuccess: () => router.replace("/dashboard"),
      onError: (error) => {
        if (
          isApiError(error, API_CODES.RATE_LIMITED) &&
          error.retryAfterSeconds !== undefined
        ) {
          setLockedOut(true);
          setTimeout(() => setLockedOut(false), error.retryAfterSeconds * 1000);
        }
      },
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
        <ErrorBanner>
          {lockout ? lockoutMessage(lockout) : messageFor(loginMutation.error)}
        </ErrorBanner>
      )}

      <Button
        type="submit"
        className="w-full"
        disabled={loginMutation.isPending || lockedOut}
      >
        {loginMutation.isPending ? "Signing in" : "Sign in"}
      </Button>
    </form>
  );
}

function lockoutMessage(error: ApiError): string {
  if (error.retryAfterSeconds === undefined) {
    return error.message;
  }

  const minutes = Math.ceil(error.retryAfterSeconds / SECONDS_PER_MINUTE);
  return `Too many attempts. Try again in ${minutes} ${
    minutes === 1 ? "minute" : "minutes"
  }.`;
}
