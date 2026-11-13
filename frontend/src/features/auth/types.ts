/** Mirrors auth/schemas/auth.py. The forms check the same limits before sending. */
export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 128;

/** RFC 5321's limit on a full address. */
export const MAX_EMAIL_LENGTH = 254;

/** Mirrors auth/schemas/auth.py: LoginRequest. */
export type LoginRequest = {
  email: string;
  password: string;
};

/** Mirrors auth/schemas/auth.py: RegisterRequest. */
export type RegisterRequest = {
  email: string;
  password: string;
};

/** Mirrors auth/schemas/auth.py: UserResponse. Nothing enforces the match. */
export type User = {
  id: number;
  email: string;
};

export type Session =
  | { status: "unknown" }
  | { status: "anonymous" }
  | { status: "unreachable"; retry: () => void }
  | { status: "authenticated"; user: User };
