"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { accountMutations, accountQueries } from "../api/accounts";

export function useAccounts() {
  return useQuery(accountQueries.list());
}

export function useCreateAccount() {
  return useMutation(accountMutations.create());
}

export function useUpdateAccount() {
  return useMutation(accountMutations.update());
}
