import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
} from "@/lib/token-storage";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "https://api.neuralshielddigital.com";

const REQUEST_TIMEOUT_MS = 15000;

type ApiOptions = RequestInit & {
  auth?: boolean;
};

type RefreshTokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type?: string;
};

let refreshPromise: Promise<string | null> | null = null;

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiRequest<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const { auth = true, signal, ...requestOptions } = options;

  try {
    let response = await performRequest(
      path,
      requestOptions,
      auth ? getAccessToken() : null,
      signal,
    );

    if (auth && response.status === 401) {
      const refreshedAccessToken = await getRefreshedAccessToken();

      if (refreshedAccessToken) {
        response = await performRequest(
          path,
          requestOptions,
          refreshedAccessToken,
          signal,
        );
      }

      if (!refreshedAccessToken || response.status === 401) {
        expireSession();

        throw new ApiError(
          401,
          "Your session has expired. Please sign in again.",
        );
      }
    }

    const payload = await readResponsePayload(response);

    if (!response.ok) {
      throw new ApiError(
        response.status,
        extractErrorDetail(payload),
      );
    }

    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (isAbortError(error)) {
      throw new ApiError(
        408,
        "Request timed out. Please check the backend connection.",
      );
    }

    if (error instanceof TypeError) {
      throw new ApiError(
        0,
        `Unable to reach backend at ${API_BASE_URL}. Check NEXT_PUBLIC_API_URL, backend status, and CORS settings.`,
      );
    }

    throw error;
  }
}

async function performRequest(
  path: string,
  requestOptions: RequestInit,
  accessToken: string | null,
  externalSignal?: AbortSignal | null,
): Promise<Response> {
  const headers = new Headers(requestOptions.headers);
  const hasBody = requestOptions.body !== undefined;
  const controller = new AbortController();

  const timeoutId = globalThis.setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  );

  const abortFromExternalSignal = () => controller.abort();

  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener(
        "abort",
        abortFromExternalSignal,
        { once: true },
      );
    }
  }

  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken}`,
    );
  } else {
    headers.delete("Authorization");
  }

  try {
    return await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      headers,
      signal: controller.signal,
    });
  } finally {
    globalThis.clearTimeout(timeoutId);

    externalSignal?.removeEventListener(
      "abort",
      abortFromExternalSignal,
    );
  }
}

async function getRefreshedAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    return null;
  }

  try {
    const response = await performRequest(
      "/api/auth/refresh",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      },
      null,
    );

    if (!response.ok) {
      return null;
    }

    const payload =
      await readResponsePayload(response) as Partial<RefreshTokenResponse>;

    if (
      typeof payload.access_token !== "string" ||
      !payload.access_token ||
      typeof payload.refresh_token !== "string" ||
      !payload.refresh_token
    ) {
      return null;
    }

    saveTokens(
      payload.access_token,
      payload.refresh_token,
    );

    return payload.access_token;
  } catch {
    return null;
  }
}

function expireSession() {
  clearTokens();

  if (typeof window === "undefined") {
    return;
  }

  if (window.location.pathname === "/login") {
    return;
  }

  const currentPath =
    window.location.pathname +
    window.location.search;

  window.location.assign(
    `/login?next=${encodeURIComponent(currentPath)}`,
  );
}

async function readResponsePayload(
  response: Response,
): Promise<unknown> {
  const contentType =
    response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

function extractErrorDetail(payload: unknown) {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload
  ) {
    const detail = (
      payload as { detail: unknown }
    ).detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (
            typeof item === "object" &&
            item !== null &&
            "msg" in item
          ) {
            return String(
              (item as { msg: unknown }).msg,
            );
          }

          return JSON.stringify(item);
        })
        .join(", ");
    }

    return JSON.stringify(detail);
  }

  if (
    typeof payload === "string" &&
    payload.trim()
  ) {
    return payload;
  }

  return "Request failed";
}

function isAbortError(error: unknown) {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  ) || (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    (error as { name: unknown }).name ===
      "AbortError"
  );
}
