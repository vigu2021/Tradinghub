const UNREACHABLE_MESSAGE = "Could not reach the server. Please try again.";
const UNEXPECTED_MESSAGE = "Something went wrong. Please try again.";

export const API_CODES = {
  INVALID_CREDENTIALS: "invalid_credentials",
  INVALID_SESSION: "invalid_session",
  EMAIL_TAKEN: "email_taken",
  RATE_LIMITED: "rate_limited",
  VALIDATION: "validation_error",
  INTERNAL: "internal_error",
} as const;

/** The codes this frontend knows how to branch on. */
export type KnownApiCode = (typeof API_CODES)[keyof typeof API_CODES];

/**
 * What an error can carry: a known code, or one the backend added since this file was written.
 * `string & {}` keeps the known ones suggestable instead of collapsing the union to `string`.
 */
export type ApiCode = KnownApiCode | (string & {});

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: ApiCode,
    readonly status: number,
    readonly retryAfterSeconds?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

/** Narrow a failure to an ApiError, optionally one carrying `code`. A typo in `code` will not compile. */
export function isApiError(
  error: unknown,
  code?: KnownApiCode,
): error is ApiError {
  return (
    error instanceof ApiError && (code === undefined || error.code === code)
  );
}

export function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof NetworkError) {
    return UNREACHABLE_MESSAGE;
  }
  return UNEXPECTED_MESSAGE;
}
