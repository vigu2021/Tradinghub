import { mutationOptions } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";

import type { Transaction } from "../types/transactions";
import type { TransferCreate } from "../types/transfers";
import { ledgerKeys } from "./keys";

export const transferMutations = {
  create: () =>
    mutationOptions({
      mutationFn: createTransfer,
      meta: { invalidates: ledgerKeys.all },
    }),
  delete: () =>
    mutationOptions({
      mutationFn: deleteTransfer,
      meta: { invalidates: ledgerKeys.all },
    }),
};

/** Returns every row written: both sides, plus the fee row if there was one. */
export async function createTransfer(
  body: TransferCreate,
): Promise<Transaction[]> {
  const { data } = await apiClient.post<Transaction[]>("/transfers", body);
  return data;
}

/** Deletes every row of the transfer, fee included. */
export async function deleteTransfer(groupId: string): Promise<void> {
  await apiClient.delete(`/transfers/${groupId}`);
}
