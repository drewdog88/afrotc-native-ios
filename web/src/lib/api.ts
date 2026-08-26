/* Thin typed fetch client over the FastAPI backend.
   Holds the JWT access/refresh pair, attaches the bearer token, and transparently
   refreshes once on a 401 before giving up. Types are pulled from the generated
   OpenAPI schema so request/response shapes stay in lockstep with the contract. */
import type { components } from "../api/schema";

type Schemas = components["schemas"];
// The backend no longer emits a bare `TokenPair` schema component (login now
// returns LoginResponse, verify returns LoginVerifyResponse). Kept as a local
// structural type; the two-step login flow (see api.login) constructs it.
export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  force_password_change?: boolean;
};
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
export type IntakeCreate = Schemas["IntakeCreate"];
export type IntakeOptions = Schemas["IntakeOptions"];
export type IntakeSubmitResult = Schemas["IntakeSubmitResult"];
export type IntakeSettingsOut = Schemas["IntakeSettingsOut"];
export type IntakeSettingsUpdate = Schemas["IntakeSettingsUpdate"];
export type TwoFAStatus = Schemas["TwoFAStatus"];
export type TrustedDeviceOut = Schemas["TrustedDeviceOut"];
// Local structural type (the OpenAPI generator isn't re-run for this client;
// see TokenPair above for the same pattern).
export type SessionOut = {
  id: number;
  device_label: string;
  ip_address: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  current: boolean;
};

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const ACCESS_KEY = "det695.access";
const REFRESH_KEY = "det695.refresh";
const TRUST_KEY = "det695.trust";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(pair: TokenPair) {
    localStorage.setItem(ACCESS_KEY, pair.access_token);
    localStorage.setItem(REFRESH_KEY, pair.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// Persists the "remember this device" token returned after a successful 2FA
// verification, so a subsequent login can skip the challenge. Never cleared
// on logout — trusting a device is independent of any one session.
export const trust = {
  get(): string | null {
    return localStorage.getItem(TRUST_KEY);
  },
  set(t: string): void {
    localStorage.setItem(TRUST_KEY, t);
  },
  clear(): void {
    localStorage.removeItem(TRUST_KEY);
  },
};

type LoginResponse = Schemas["LoginResponse"];
type LoginVerifyResponse = Schemas["LoginVerifyResponse"];

export type LoginResult =
  | { kind: "authed" }
  | { kind: "challenge"; challengeToken: string; method: string };

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
  async login(username: string, password: string): Promise<LoginResult> {
    const res = await request<LoginResponse>("/auth/login", {
      method: "POST",
      auth: false,
      body: { username, password, trust_token: trust.get() ?? undefined },
    });
    if (res.two_factor_required) {
      return {
        kind: "challenge",
        challengeToken: res.challenge_token as string,
        method: res.method ?? "email",
      };
    }
    tokens.set({
      access_token: res.access_token as string,
      refresh_token: res.refresh_token as string,
      token_type: res.token_type ?? "bearer",
      force_password_change: res.force_password_change ?? false,
    });
    return { kind: "authed" };
  },
  async loginVerify(challengeToken: string, code: string, trustDevice: boolean): Promise<void> {
    const res = await request<LoginVerifyResponse>("/auth/login/verify", {
      method: "POST",
      auth: false,
      body: { challenge_token: challengeToken, code, trust_device: trustDevice },
    });
    tokens.set({
      access_token: res.access_token,
      refresh_token: res.refresh_token,
      token_type: res.token_type ?? "bearer",
      force_password_change: res.force_password_change ?? false,
    });
    if (res.trust_token) trust.set(res.trust_token);
  },
  async loginResend(challengeToken: string): Promise<void> {
    await request("/auth/login/resend", {
      method: "POST",
      auth: false,
      body: { challenge_token: challengeToken },
    });
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

  // Intake form endpoints (public, unauthenticated)
  intakeOptions: () => request<IntakeOptions>("/intake/options", { auth: false }),
  submitIntake: (body: IntakeCreate) =>
    request<IntakeSubmitResult>("/intake", { method: "POST", auth: false, body }),
  getIntakeSettings: () => request<IntakeSettingsOut>("/admin/intake-settings"),
  updateIntakeSettings: (body: IntakeSettingsUpdate) =>
    request<IntakeSettingsOut>("/admin/intake-settings", { method: "PUT", body }),
  adminRevokeTrustedDevices: (userId: number) =>
    request<{ detail: string }>(`/admin/users/${userId}/revoke-trusted-devices`, { method: "POST" }),

  // Profile 2FA settings + trusted-device management.
  twoFAStatus: () => request<TwoFAStatus>("/profile/2fa/status"),
  twoFAEnroll: () => request<void>("/profile/2fa/enroll", { method: "POST", body: { method: "email" } }),
  twoFAEnrollVerify: (code: string) =>
    request<void>("/profile/2fa/enroll/verify", { method: "POST", body: { code } }),
  twoFAEnrollmentDismiss: () => request<void>("/profile/2fa/enrollment-dismiss", { method: "POST" }),
  twoFADisable: () => request<void>("/profile/2fa/disable", { method: "POST" }),
  listTrustedDevices: () => request<TrustedDeviceOut[]>("/profile/trusted-devices"),
  revokeTrustedDevice: (id: number) => request<void>(`/profile/trusted-devices/${id}`, { method: "DELETE" }),
  revokeOtherTrustedDevices: () =>
    request<void>("/profile/trusted-devices/revoke-others", {
      method: "POST",
      body: { trust_token: trust.get() ?? undefined },
    }),

  // Profile session tracking.
  listSessions: () => request<SessionOut[]>("/profile/sessions"),
  revokeSession: (id: number) => request<void>(`/profile/sessions/${id}`, { method: "DELETE" }),
  revokeOtherSessions: () => request<void>("/profile/sessions/revoke-others", { method: "POST" }),
};
