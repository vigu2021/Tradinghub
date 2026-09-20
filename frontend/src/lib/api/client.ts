import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { API_CODES, ApiError, isApiError, NetworkError } from "./errors";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const DEFAULT_REQUEST_TIMEOUT_MS = 10_000;
const REFRESH_PATH = "/auth/refresh";

/** Untrusted JSON: every field optional. */
type Envelope = { error?: { code?: string; message?: string } };

type Retriable = InternalAxiosRequestConfig & { retried?: boolean };

export const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  timeout: DEFAULT_REQUEST_TIMEOUT_MS,
});

function toFailure(error: AxiosError): ApiError | NetworkError {
  if (!error.response) {
    return new NetworkError(error.message);
  }

  // A proxy or a gateway answers in its own shape: nothing here to render.
  const envelope = (error.response.data as Envelope | null | undefined)?.error;
  if (!envelope?.code || !envelope.message) {
    return new NetworkError(error.message);
  }

  const retryAfterSeconds =
    Number(error.response.headers["retry-after"]) || undefined;

  return new ApiError(
    envelope.message,
    envelope.code,
    error.response.status,
    retryAfterSeconds,
  );
}

// Two refreshes carrying one token read as theft. The promise serialises them within a tab, the
// browser lock between tabs.
const REFRESH_LOCK = "tradinghub-refresh";
let refreshInFlight: Promise<boolean> | null = null;

function rotateSessionOnce(): Promise<boolean> {
  refreshInFlight ??= navigator.locks
    .request(REFRESH_LOCK, () => apiClient.post(REFRESH_PATH))
    .then(() => true)
    .catch((error: unknown) => {
      // Only the API refusing means the session is gone. A refresh that never arrived says nothing.
      if (isApiError(error)) {
        return false;
      }
      throw error;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

// A wrong password is a 401 too, and refreshing on those spends a rotation per typo. The refresh
// call is excluded because it runs through this interceptor and would recurse.
function shouldRotateAndReplay(
  failure: ApiError | NetworkError,
  config: Retriable | undefined,
): config is Retriable {
  return (
    isApiError(failure, API_CODES.INVALID_SESSION) &&
    config !== undefined &&
    config.url !== REFRESH_PATH &&
    !config.retried
  );
}

apiClient.interceptors.response.use(null, async (error: unknown) => {
  if (!axios.isAxiosError(error)) {
    throw error;
  }

  const failure = toFailure(error);
  const config = error.config as Retriable | undefined;

  if (shouldRotateAndReplay(failure, config) && (await rotateSessionOnce())) {
    // Returning here resolves the caller's promise, so the retry is invisible to them.
    config.retried = true;
    return apiClient.request(config);
  }

  throw failure;
});
