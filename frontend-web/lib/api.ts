import { getAccessToken } from "@/lib/token-storage";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const REQUEST_TIMEOUT_MS = 15000;

type ApiOptions = RequestInit & {
  auth?: boolean;
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { auth = true, signal, ...requestOptions } = options;
  const headers = new Headers(options.headers);
  const hasBody = options.body !== undefined;
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = getAccessToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  if (signal) {
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      headers,
      signal: controller.signal
    });

    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      const detail = extractErrorDetail(payload);
      throw new ApiError(response.status, detail);
    }

    return payload as T;
  } catch (error) {
    if (isAbortError(error)) {
      throw new ApiError(408, "Request timed out. Please check the backend connection.");
    }
    if (error instanceof TypeError) {
      throw new ApiError(
        0,
        `Unable to reach backend at ${API_BASE_URL}. Check NEXT_PUBLIC_API_URL, backend status, and CORS settings.`
      );
    }
    throw error;
  } finally {
    globalThis.clearTimeout(timeoutId);
  }
}

function extractErrorDetail(payload: unknown) {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join(", ");
    }
    return JSON.stringify(detail);
  }

  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }

  return "Request failed";
}

function isAbortError(error: unknown) {
  return (
    error instanceof DOMException && error.name === "AbortError"
  ) || (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    (error as { name: unknown }).name === "AbortError"
  );
}
