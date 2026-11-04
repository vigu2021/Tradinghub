import { queryOptions } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";

import type { Account, AccountCreate, AccountUpdate } from "../types/accounts";
import { ledgerKeys } from "./keys";

export const accountKeys = {
  all: [...ledgerKeys.all, "accounts"] as const,
  list: () => [...accountKeys.all, "list"] as const,
};

export const accountQueries = {
  list: () =>
    queryOptions({ queryKey: accountKeys.list(), queryFn: listAccounts }),
};

/** Every account, archived ones included, by name. */
export async function listAccounts(): Promise<Account[]> {
  const { data } = await apiClient.get<Account[]>("/accounts");
  return data;
}

export async function createAccount(body: AccountCreate): Promise<Account> {
  const { data } = await apiClient.post<Account>("/accounts", body);
  return data;
}

/** Sends only the fields that changed. Archive or restore with `{ archived: true | false }`. */
export async function updateAccount(
  id: number,
  changes: AccountUpdate,
): Promise<Account> {
  const { data } = await apiClient.patch<Account>(`/accounts/${id}`, changes);
  return data;
}
