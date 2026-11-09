import { mutationOptions, queryOptions } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";

import type {
  Transaction,
  TransactionCreate,
  TransactionFilters,
  TransactionPage,
  TransactionUpdate,
} from "../types/transactions";
import { ledgerKeys } from "./keys";

export const transactionKeys = {
  all: [...ledgerKeys.all, "transactions"] as const,
  list: (filters: TransactionFilters) =>
    [...transactionKeys.all, "list", filters] as const,
};

export const transactionQueries = {
  list: (filters: TransactionFilters) =>
    queryOptions({
      queryKey: transactionKeys.list(filters),
      queryFn: () => listTransactions(filters),
    }),
};

export const transactionMutations = {
  create: () =>
    mutationOptions({
      mutationFn: createTransaction,
      meta: { invalidates: ledgerKeys.all },
    }),
  update: () =>
    mutationOptions({
      mutationFn: updateTransaction,
      meta: { invalidates: ledgerKeys.all },
    }),
  delete: () =>
    mutationOptions({
      mutationFn: deleteTransaction,
      meta: { invalidates: ledgerKeys.all },
    }),
};

/** One page of the user's transactions, transfer rows included, newest first. */
export async function listTransactions(
  filters: TransactionFilters,
): Promise<TransactionPage> {
  const { data } = await apiClient.get<TransactionPage>("/transactions", {
    params: filters,
  });
  return data;
}

export async function createTransaction(
  body: TransactionCreate,
): Promise<Transaction> {
  const { data } = await apiClient.post<Transaction>("/transactions", body);
  return data;
}

type UpdateTransactionVariables = { id: number; changes: TransactionUpdate };

/** Sends only the fields that changed. A transfer row is refused with a 409. */
export async function updateTransaction({
  id,
  changes,
}: UpdateTransactionVariables): Promise<Transaction> {
  const { data } = await apiClient.patch<Transaction>(
    `/transactions/${id}`,
    changes,
  );
  return data;
}

/** Deletes one income or expense row. A transfer row is refused with a 409. */
export async function deleteTransaction(id: number): Promise<void> {
  await apiClient.delete(`/transactions/${id}`);
}
