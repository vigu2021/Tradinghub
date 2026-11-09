"use client";

import {
  MutationCache,
  QueryClient,
  QueryClientProvider,
  type QueryKey,
} from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { isApiError } from "@/lib/api/errors";

declare module "@tanstack/react-query" {
  // Augmenting the library's Register only works through an interface.
  // eslint-disable-next-line @typescript-eslint/consistent-type-definitions
  interface Register {
    mutationMeta: { invalidates?: QueryKey };
  }
}

const STALE_TIME_MS = 2 * 60_000;
const MAX_NETWORK_RETRIES = 2;

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        mutationCache: new MutationCache({
          // Returned so the mutation stays pending until the refetch lands.
          onSuccess: (
            _data,
            _variables,
            _result,
            _mutation,
            { client, meta },
          ) =>
            meta?.invalidates &&
            client.invalidateQueries({ queryKey: meta.invalidates }),
        }),
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
