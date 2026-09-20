"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createContext, useContext } from "react";

import { API_CODES, isApiError } from "@/lib/api/errors";

import { authKeys, getCurrentUser, login, logout, register } from "./api";
import type { LoginRequest, RegisterRequest, Session, User } from "./types";

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
  const router = useRouter();

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });
}

export function useUser() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: getCurrentUser,
  });
}

/** Derived from the query's status, never its data: a failed refetch keeps the last user around. */
export function useSession(): Session {
  const query = useUser();

  if (query.status === "pending") {
    return { status: "unknown" };
  }

  if (query.status === "error") {
    return isApiError(query.error, API_CODES.INVALID_SESSION)
      ? { status: "anonymous" }
      : { status: "unreachable", retry: () => void query.refetch() };
  }

  return { status: "authenticated", user: query.data };
}

/** Filled by the signed-in layout, so every page beneath it can read the user without a check. */
export const AuthenticatedUserContext = createContext<User | null>(null);

export function useAuthenticatedUser(): User {
  const user = useContext(AuthenticatedUserContext);
  if (user === null) {
    throw new Error(
      "useAuthenticatedUser was called outside the signed-in layout",
    );
  }
  return user;
}
