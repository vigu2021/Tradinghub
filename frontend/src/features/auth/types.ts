import { z } from "zod";

export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 128;

/** RFC 5321's limit on a full address. */
export const MAX_EMAIL_LENGTH = 254;

const emailField = z
  .email("Please enter a valid email.")
  .max(MAX_EMAIL_LENGTH, "That email is too long.");

export const loginSchema = z.object({
  email: emailField,
  password: z
    .string()
    .min(1, "Enter your password.")
    .max(MAX_PASSWORD_LENGTH, "That password is too long."),
});

export const registerSchema = z.object({
  email: emailField,
  password: z
    .string()
    .min(MIN_PASSWORD_LENGTH, `Use at least ${MIN_PASSWORD_LENGTH} characters.`)
    .max(MAX_PASSWORD_LENGTH, "That password is too long."),
});

export type LoginRequest = z.infer<typeof loginSchema>;
export type RegisterRequest = z.infer<typeof registerSchema>;

/** Mirrors auth/schemas/auth.py: UserResponse. Nothing enforces the match. */
export interface User {
  id: number;
  email: string;
}
