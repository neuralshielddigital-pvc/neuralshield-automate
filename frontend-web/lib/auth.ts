import { ApiError, apiRequest } from "@/lib/api";
import { saveTokens } from "@/lib/token-storage";
import type { AuthResponse, CurrentUserResponse } from "@/lib/types";

export async function login(email: string, password: string) {
  const response = await apiRequest<AuthResponse>("/api/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ email: email.trim(), password })
  });
  assertAuthResponse(response);
  saveTokens(response.access_token, response.refresh_token);
  return response;
}

export async function signup(email: string, password: string, tenantName: string, ref?: string | null) {
  const response = await apiRequest<AuthResponse>("/api/auth/signup", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      email,
      password,
      tenant_name: tenantName,
      ref: ref || undefined
    })
  });
  assertAuthResponse(response);
  saveTokens(response.access_token, response.refresh_token);
  return response;
}

export async function getMe() {
  return apiRequest<CurrentUserResponse>("/api/auth/me");
}

function assertAuthResponse(response: AuthResponse) {
  if (!response.access_token || !response.refresh_token) {
    throw new ApiError(502, "Login response did not include access_token and refresh_token.");
  }
}
