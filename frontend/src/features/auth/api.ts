import { apiClient } from "@/lib/api/client";
import { LoginRequest, RegisterRequest, User } from "./types";

export const authKeys = {
  me: ["auth", "me"] as const,
};

export async function login(body: LoginRequest): Promise<User> {
  const { data } = await apiClient.post<User>("/auth/login", body);
  return data;
}

export async function register(body: RegisterRequest): Promise<User> {
  const { data } = await apiClient.post<User>("/auth/register", body);
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<User>("/auth/me");
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}
