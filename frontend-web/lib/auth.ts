import { ApiError, apiRequest } from "@/lib/api";
import {
  getAccessToken as getStoredAccessToken,
  saveTokens,
} from "@/lib/token-storage";
import type { AuthResponse, CurrentUserResponse } from "@/lib/types";

type MessageResponse = {
  message: string;
};

export async function login(email: string, password: string) {
  const response = await apiRequest<AuthResponse>("/api/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      email: email.trim(),
      password,
    }),
  });

  assertAuthResponse(response);

  saveTokens(
    response.access_token,
    response.refresh_token,
  );

  return response;
}

export async function signup(
  email: string,
  password: string,
  tenantName: string,
  ref?: string | null,
) {
  const response = await apiRequest<AuthResponse>("/api/auth/signup", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      email: email.trim(),
      password,
      tenant_name: tenantName.trim(),
      ref: ref || undefined,
    }),
  });

  assertAuthResponse(response);

  saveTokens(
    response.access_token,
    response.refresh_token,
  );

  return response;
}

export async function verifyEmail(token: string) {
  return apiRequest<{ message: string }>("/api/auth/verify-email", {
    method: "POST",
    auth: false,
    body: JSON.stringify({
      token,
    }),
  });
}

export async function resendVerificationEmail(email: string) {
  return apiRequest<{ message: string }>(
    "/api/auth/resend-verification-email",
    {
      method: "POST",
      auth: false,
      body: JSON.stringify({
        email: email.trim(),
      }),
    },
  );
}

export async function forgotPassword(
  email: string,
): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(
    "/api/auth/forgot-password",
    {
      method: "POST",
      auth: false,
      body: JSON.stringify({
        email: email.trim(),
      }),
    },
  );
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(
    "/api/auth/reset-password",
    {
      method: "POST",
      auth: false,
      body: JSON.stringify({
        token,
        new_password: newPassword,
      }),
    },
  );
}

export async function getMe() {
  return apiRequest<CurrentUserResponse>(
    "/api/auth/me",
  );
}

export function getAccessToken() {
  return getStoredAccessToken();
}

function assertAuthResponse(
  response: AuthResponse,
) {
  if (
    !response.access_token ||
    !response.refresh_token
  ) {
    throw new ApiError(
      502,
      "Login response did not include access_token and refresh_token.",
    );
  }
}
