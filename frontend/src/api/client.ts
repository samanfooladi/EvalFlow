import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

/**
 * Access token lives only in memory (module scope) — never in
 * localStorage/sessionStorage where XSS could read it. The refresh token
 * is an httpOnly cookie managed entirely by the server.
 */
let accessToken: string | null = null;
let onSessionExpired: (() => void) | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

export const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  // De-duplicate concurrent 401s into a single refresh call.
  refreshPromise ??= axios
    .post<{ access: string }>("/api/v1/auth/refresh/", null, {
      withCredentials: true,
    })
    .then((res) => {
      setAccessToken(res.data.access);
      return res.data.access;
    })
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retried?: boolean;
    };
    const url = original?.url ?? "";
    if (
      error.response?.status === 401 &&
      !original._retried &&
      !url.includes("/auth/login") &&
      !url.includes("/auth/refresh")
    ) {
      original._retried = true;
      try {
        const token = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        setAccessToken(null);
        onSessionExpired?.();
      }
    }
    return Promise.reject(error);
  },
);

/** Extract a human-readable Persian error message from a DRF response. */
export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data as Record<string, unknown>;
    if (typeof data.detail === "string") return data.detail;
    const first = Object.values(data)[0];
    if (Array.isArray(first) && typeof first[0] === "string") return first[0];
    if (typeof first === "string") return first;
  }
  return "خطایی رخ داد. لطفاً دوباره تلاش کنید.";
}
