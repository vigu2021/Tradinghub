"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Field } from "@/components/ui/Field";
import { API_CODES, isApiError, messageFor } from "@/lib/api/errors";

import { useRegister } from "../hooks";
import {
  MAX_EMAIL_LENGTH,
  MAX_PASSWORD_LENGTH,
  MIN_PASSWORD_LENGTH,
} from "../types";

const registerSchema = z.object({
  email: z
    .email("Please enter a valid email.")
    .max(MAX_EMAIL_LENGTH, "That email is too long."),
  password: z
    .string()
    .min(MIN_PASSWORD_LENGTH, `Use at least ${MIN_PASSWORD_LENGTH} characters.`)
    .max(MAX_PASSWORD_LENGTH, "That password is too long."),
});

type RegisterValues = z.infer<typeof registerSchema>;

export function RegisterForm() {
  const router = useRouter();
  const registerMutation = useRegister();
  const {
    register: field,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    mode: "onTouched",
  });

  const submit = handleSubmit((values) => {
    registerMutation.mutate(values, {
      onSuccess: () => router.replace("/dashboard"),
    });
  });

  const emailTaken = isApiError(registerMutation.error, API_CODES.EMAIL_TAKEN);

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
        <ErrorBanner>
          {messageFor(registerMutation.error)}{" "}
          {emailTaken && (
            <Link
              href="/login"
              className="underline decoration-danger/40 underline-offset-4 hover:decoration-danger"
            >
              Sign in instead
            </Link>
          )}
        </ErrorBanner>
      )}

      <Button
        type="submit"
        className="w-full"
        disabled={registerMutation.isPending}
      >
        {registerMutation.isPending ? "Creating account" : "Create account"}
      </Button>
    </form>
  );
}
