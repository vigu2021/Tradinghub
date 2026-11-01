"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { isApiError } from "@/lib/api/errors";

const STALE_TIME_MS = 2 * 60_000;
const MAX_NETWORK_RETRIES = 2;

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: STALE_TIME_MS,
            retry: (failureCount, error) =>
              !isApiError(error) && failureCount < MAX_NETWORK_RETRIES,
            networkMode: "always",
          },
          // The default pauses requests while offline, which leaves the screen waiting with no error.
          mutations: { networkMode: "always" },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
