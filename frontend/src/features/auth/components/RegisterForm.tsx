"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

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
        autoComplete="new-password"
        aria-describedby="password-hint"
        aria-invalid={Boolean(errors.password)}
        {...field("password")}
      />
      <p id="password-hint">At least {MIN_PASSWORD_LENGTH} characters</p>
      {errors.password && <p role="alert">{errors.password.message}</p>}

      {registerMutation.error && (
        <p role="alert">
          {messageFor(registerMutation.error)}{" "}
          {emailTaken && <Link href="/login">Log in instead</Link>}
        </p>
      )}

      <button type="submit" disabled={registerMutation.isPending}>
        {registerMutation.isPending ? "Creating account…" : "Create account"}
      </button>
    </form>
  );
}
