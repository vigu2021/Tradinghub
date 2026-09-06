import { z } from "zod";

export const MIN_PASSWORD_LENGTH = 8;

export const loginSchema = z.object({
  email: z.email("Please enter a valid email."),
  password: z.string().min(1, "Enter your password."),
});

export const registerSchema = z.object({
  email: z.email("Please enter a valid email."),
  password: z
    .string()
    .min(
      MIN_PASSWORD_LENGTH,
      `Use at least ${MIN_PASSWORD_LENGTH} characters.`,
    ),
});

export type LoginRequest = z.infer<typeof loginSchema>;
export type RegisterRequest = z.infer<typeof registerSchema>;

/** Mirrors auth/schemas/auth.py: UserResponse. Nothing enforces the match. */
export interface User {
  id: number;
  email: string;
}
