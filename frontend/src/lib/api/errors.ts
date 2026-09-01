const UNREACHABLE_MESSAGE = "Could not reach the server. Please try again.";
const UNEXPECTED_MESSAGE = "Something went wrong. Please try again.";

export const API_CODES = {
  INVALID_CREDENTIALS: "invalid_credentials",
  INVALID_SESSION: "invalid_session",
  EMAIL_TAKEN: "email_taken",
  VALIDATION: "validation_error",
  INTERNAL: "internal_error",
} as const;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
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

export function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof NetworkError) {
    return UNREACHABLE_MESSAGE;
  }
  return UNEXPECTED_MESSAGE;
}
