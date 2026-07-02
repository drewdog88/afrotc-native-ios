/* Thin typed fetch client over the FastAPI backend.
   Holds the JWT access/refresh pair, attaches the bearer token, and transparently
   refreshes once on a 401 before giving up. Types are pulled from the generated
   OpenAPI schema so request/response shapes stay in lockstep with the contract. */
import type { components } from "../api/schema";

type Schemas = components["schemas"];
export type TokenPair = Schemas["TokenPair"];
export type UserOut = Schemas["UserOut"];
export type DashboardStats = Schemas["DashboardStats"];
export type FunnelResponse = Schemas["FunnelResponse"];
export type FunnelStageCount = Schemas["FunnelStageCount"];
export type TrendsResponse = Schemas["TrendsResponse"];
export type TrendSeries = Schemas["TrendSeries"];
export type TrendPoint = Schemas["TrendPoint"];
export type RecruitOut = Schemas["RecruitOut"];
export type RecruitCreate = Schemas["RecruitCreate"];
export type RecruitUpdate = Schemas["RecruitUpdate"];
export type RecruitPage = Schemas["Page_RecruitOut_"];
export type StageChange = Schemas["StageChange"];
export type StageEventOut = Schemas["StageEventOut"];
export type RecruitStage = Schemas["RecruitStage"];

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const ACCESS_KEY = "det695.access";
const REFRESH_KEY = "det695.refresh";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(pair: { access_token: string; refresh_token: string }) {
    localStorage.setItem(ACCESS_KEY, pair.access_token);
    localStorage.setItem(REFRESH_KEY, pair.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

function messageFromDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string };
    if (first?.msg) return first.msg;
  }
  return fallback;
}

async function refreshTokens(): Promise<boolean> {
  const refresh = tokens.refresh;
  if (!refresh) return false;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    tokens.clear();
    return false;
  }
  const pair = (await res.json()) as TokenPair;
  tokens.set(pair);
  return true;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  raw?: boolean; // return the Response instead of parsed JSON (file downloads)
  isForm?: boolean; // body is FormData; don't JSON-encode or set content-type
}

async function request<T>(path: string, opts: RequestOptions = {}, retry = true): Promise<T> {
  const { method = "GET", body, auth = true, raw = false, isForm = false } = opts;
  const headers: Record<string, string> = {};
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;

  let payload: BodyInit | undefined;
  if (body !== undefined) {
    if (isForm) {
      payload = body as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
  }

  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload });

  if (res.status === 401 && auth && retry && (await refreshTokens())) {
    return request<T>(path, opts, false);
  }

  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = (await res.json())?.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail, messageFromDetail(detail, `Request failed (${res.status})`));
  }

  if (raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form, isForm: true }),
  raw: (path: string) => request<Response>(path, { raw: true }),

  // Auth is special: login doesn't send a bearer, and stores the returned pair.
  async login(username: string, password: string, totp_code?: string): Promise<TokenPair> {
    const pair = await request<TokenPair>("/auth/login", {
      method: "POST",
      auth: false,
      body: { username, password, totp_code },
    });
    tokens.set(pair);
    return pair;
  },
  async logout(): Promise<void> {
    try {
      await request("/auth/logout", { method: "POST" });
    } catch {
      /* best-effort; clear locally regardless */
    }
    tokens.clear();
  },
  me: () => request<UserOut>("/auth/me"),
};
