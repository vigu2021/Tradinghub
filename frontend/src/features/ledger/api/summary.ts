import { queryOptions } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";

import type { Summary, SummaryPeriod } from "../types/summary";
import { ledgerKeys } from "./keys";

export const summaryKeys = {
  all: [...ledgerKeys.all, "summary"] as const,
  period: (period: SummaryPeriod) => [...summaryKeys.all, period] as const,
};

export const summaryQueries = {
  period: (period: SummaryPeriod) =>
    queryOptions({
      queryKey: summaryKeys.period(period),
      queryFn: () => getSummary(period),
    }),
};

export async function getSummary(period: SummaryPeriod): Promise<Summary> {
  const { data } = await apiClient.get<Summary>("/summary", { params: period });
  return data;
}
