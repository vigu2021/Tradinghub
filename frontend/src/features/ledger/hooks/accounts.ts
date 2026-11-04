"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { accountQueries, createAccount, updateAccount } from "../api/accounts";
import { ledgerKeys } from "../api/keys";

export function useAccounts() {
  return useQuery(accountQueries.list());
}

export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAccount,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ledgerKeys.all }),
  });
}

export function useUpdateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateAccount,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ledgerKeys.all }),
  });
}
