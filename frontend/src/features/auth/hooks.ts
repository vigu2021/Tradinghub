"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authKeys, getCurrentUser, login, logout, register } from "./api";
import type { LoginRequest, RegisterRequest } from "./types";

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: LoginRequest) => login(body),
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me, user);
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: RegisterRequest) => register(body),
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me, user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.clear();
    },
  });
}

export function useUser() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: getCurrentUser,
  });
}
