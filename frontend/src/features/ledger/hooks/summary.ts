"use client";

import { useQuery } from "@tanstack/react-query";

import { summaryQueries } from "../api/summary";
import type { SummaryPeriod } from "../types/summary";

export function useSummary(period: SummaryPeriod) {
  return useQuery(summaryQueries.period(period));
}
