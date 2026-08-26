# Email-2FA Web Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the already-shipped email-2FA backend into the React web client — a dedicated login verify screen, first-login enrollment prompt, Profile email-2FA + trusted-device management, and an admin 2FA toggle — so 2FA is usable end-to-end on the web.

**Architecture:** The web app is React 19 + React Router 7 + TanStack Query v5 + Vite + TypeScript, with a hand-rolled typed `fetch` wrapper (`src/lib/api.ts`) and a React Context auth store (`src/lib/auth.tsx`). Auth is Bearer-JWT in localStorage (**no cookies**). The 2FA login flow becomes two-step: `POST /auth/login` returns *either* a `TokenPair` *or* a `{two_factor_required, challenge_token}` challenge; on a challenge the user is routed to a new `/login/verify` screen that calls `POST /auth/login/verify`. Trusted-device identity is carried as an opaque `trust_token` persisted in localStorage and sent in the login **body** (never a cookie). The generated `src/api/schema.d.ts` is regenerated from the backend OpenAPI after a small backend addition.

**Tech Stack:** React 19, react-router-dom 7, @tanstack/react-query 5, Vite 8, TypeScript, oxlint, CSS Modules + global utility classes. New: Vitest + @testing-library/react + jsdom for tests. Backend touch: FastAPI (one endpoint gains an optional body field).

**Spec:** `docs/superpowers/specs/2026-08-25-email-2fa-design.md` (the "Clients → Web" section, plus the API contract). Read it alongside this plan.

## Global Constraints

- **Auth transport:** Bearer JWT in localStorage (keys `det695.access` / `det695.refresh` via the existing `tokens` object in `src/lib/api.ts`). Do **not** introduce cookies for auth.
- **Trust-token transport (RULING):** the web stores the trusted-device token in localStorage under key `det695.trust` and sends it as the `trust_token` field in the `/auth/login` request body. After a successful verify with "trust this device", persist the returned `trust_token`. On explicit logout, **do not** clear the trust token (it should survive logout so the device stays trusted); clear it only when the user revokes the current device. The backend also sets a Secure httpOnly cookie, which is harmless and ignored by this client.
- **`schema.d.ts` is generated — never hand-edit it.** Regenerate via the documented two-step (backend export + `openapi-typescript`). All request/response types come from `components["schemas"][...]`.
- **Field names come from the backend.** `UserOut` exposes `two_factor_enabled`, `two_factor_method`, `two_factor_enrollment_prompted`, and `is_2fa_active`. The enrollment prompt gate is: `!two_factor_enabled && !two_factor_enrollment_prompted`.
- **Code policy (display only; backend enforces):** 6-digit numeric code, 10-min expiry, max 5 verify attempts (challenge invalidated after), 60-second resend cooldown, max 3 resends. The verify screen surfaces these (countdown, disabled resend) but the backend is the source of truth — always handle the backend's 400/429 responses.
- **Styling:** reuse global utility classes from `src/index.css` (`.card`, `.btn`/`.btn-primary`/`.btn-ghost`, `.input`, `.field-label`, `.mono`) and per-file CSS Modules where a page already has one. Model new 2FA UI on the existing `TwoFactorCard` in `src/pages/Profile.tsx`.
- **Data patterns:** reads via `useQuery` with array query keys; writes via `useMutation` with `onSuccess` invalidation + toast (`notify`) and `onError` → `ApiError` message. Keep the existing conventions.
- **Lint:** `npm run lint` (oxlint) must pass. **Types:** `npm run build` (`tsc -b`) must pass.
- **Tests:** new Vitest harness; `npm test` must pass. TDD applies to `src/lib/api.ts` 2FA functions and the verify-screen logic.

---

## File Structure

- `backend/app/schemas/profile.py` — add `RevokeOthersRequest` (optional `trust_token`).
- `backend/app/api/v1/profile.py` — `revoke-others` accepts the body token (fallback to cookie).
- `backend/tests/test_trusted_devices_api.py` — test the body-token path.
- `shared/openapi.json`, `web/src/api/schema.d.ts` — regenerated (not hand-edited).
- `web/package.json`, `web/vitest.config.ts`, `web/src/test/setup.ts` — new test harness.
- `web/src/lib/api.ts` — trust-token storage, two-step login (`login` returns a discriminated result), `loginVerify`, `loginResend`, and profile/trusted-device 2FA calls.
- `web/src/lib/api.2fa.test.ts` (or colocated `*.test.ts`) — api-layer tests.
- `web/src/lib/auth.tsx` — `login` returns challenge-or-authed; `completeVerify` finishes a challenge.
- `web/src/pages/Login.tsx` — remove the 401-reveal TOTP field; navigate to `/login/verify` on a challenge.
- `web/src/pages/LoginVerify.tsx` (new) + route in `web/src/main.tsx` — the verify screen.
- `web/src/components/EnrollmentPrompt.tsx` (new) — one-time modal, mounted in `AppShell`.
- `web/src/pages/Profile.tsx` — replace `TwoFactorCard` (TOTP) with email-2FA enable/disable + a Trusted Devices card.
- `web/src/pages/Admin.tsx` — 2FA enable/disable toggle + "revoke trusted devices" action.

---

### Task 1: Backend — `revoke-others` accepts a body `trust_token`

**Files:**
- Modify: `backend/app/schemas/profile.py`
- Modify: `backend/app/api/v1/profile.py` (`revoke_other_trusted_devices`, ~line 139)
- Test: `backend/tests/test_trusted_devices_api.py`

**Interfaces:**
- Consumes: `trusted_devices.revoke_all(db, user, except_token=...)`.
- Produces: `POST /profile/trusted-devices/revoke-others` accepts an optional JSON body `{trust_token?}`; the current device is preserved when the token is supplied in the body OR the cookie.

Run backend tests from `backend/`: `cd backend && uv run pytest -q`. New non-test modules must use `from app.core import security; security.now_utc()` (attribute access) — not relevant here but keep the rule.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_trusted_devices_api.py
def test_revoke_others_preserves_current_device_via_body_token(
    client: TestClient, make_user, monkeypatch
) -> None:
    _fixed(monkeypatch)
    make_user("dvbody", "Recruit123!", two_factor_enabled=True, two_factor_method="email")
    # First trusted login → device A (this is the "current" device / token).
    tokens_a = _login_2fa_with_trust(client, "dvbody", "Recruit123!")
    current = tokens_a["trust_token"]
    headers = {"Authorization": f"Bearer {tokens_a['access_token']}"}
    # Second trusted login → device B.
    _login_2fa_with_trust(client, "dvbody", "Recruit123!")
    assert len(client.get("/api/v1/profile/trusted-devices", headers=headers).json()) == 2

    # Revoke others, presenting device A's token in the BODY (no cookie reliance).
    resp = client.post(
        "/api/v1/profile/trusted-devices/revoke-others",
        headers=headers,
        json={"trust_token": current},
    )
    assert resp.status_code == 200
    remaining = client.get("/api/v1/profile/trusted-devices", headers=headers).json()
    assert len(remaining) == 1  # device A survived
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_trusted_devices_api.py::test_revoke_others_preserves_current_device_via_body_token -v`
Expected: FAIL (endpoint ignores the body; both devices revoked → `len == 0`).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/schemas/profile.py`, add near the other profile schemas:

```python
class RevokeOthersRequest(BaseModel):
    trust_token: str | None = None
```

(Confirm `from pydantic import BaseModel` is already imported in that file; it is used by the existing schemas.)

In `backend/app/api/v1/profile.py`, update the endpoint (import `RevokeOthersRequest` from `app.schemas.profile`; `Body` from fastapi is not needed — use the model):

```python
@router.post("/trusted-devices/revoke-others", response_model=Message)
def revoke_other_trusted_devices(
    request: Request,
    body: RevokeOthersRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Message:
    cookie_token = request.cookies.get(settings.trusted_device_cookie_name)
    current = (body.trust_token if body else None) or cookie_token
    n = trusted_devices.revoke_all(db, user, except_token=current)
    return Message(detail=f"Revoked {n} device(s)")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_trusted_devices_api.py -v`
Expected: PASS (new test + existing revoke-others test still green — the cookie path is preserved because `body` is optional).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/profile.py backend/app/api/v1/profile.py backend/tests/test_trusted_devices_api.py
git commit -m "feat(backend): accept trust_token in revoke-others body for cookieless clients"
```

---

### Task 2: Regenerate the OpenAPI contract + web schema types

**Files:**
- Regenerate: `shared/openapi.json`
- Regenerate: `web/src/api/schema.d.ts`

**Interfaces:**
- Produces: the generated TypeScript types for every 2FA endpoint and schema (`LoginResponse`, `LoginVerifyRequest`, `LoginVerifyResponse`, `ResendRequest`, `TwoFAStatus`, `TwoFAEnrollRequest`, `TrustedDeviceOut`, `RevokeOthersRequest`, and the new `UserOut`/`AdminUserUpdate` fields) that Tasks 4–11 import.

This task depends on Task 1 (so `revoke-others`'s body type is in the contract).

- [ ] **Step 1: Regenerate both artifacts**

```bash
cd backend && uv run python scripts/export_openapi.py
cd ../web && npx openapi-typescript ../shared/openapi.json -o src/api/schema.d.ts
```

- [ ] **Step 2: Verify the new endpoints and schemas are present**

Run (from repo root):
```bash
grep -o -e "login/verify" -e "login/resend" -e "2fa/enroll" -e "trusted-devices" shared/openapi.json | sort -u
grep -o -e "two_factor_enabled" -e "challenge_token" -e "TrustedDeviceOut" web/src/api/schema.d.ts | sort -u
```
Expected: all present (non-empty). If `export_openapi.py` fails to import the app, fix the import/env before proceeding — do not hand-edit the JSON.

- [ ] **Step 3: Confirm the web still type-checks and lints**

Run: `cd web && npm run build && npm run lint`
Expected: PASS (regeneration alone should not break existing code; if `TwoFAStatus`/`TwoFASetupResponse` shapes changed, that surfaces here — those are fixed in Task 10, so a *temporary* type error confined to `Profile.tsx` is acceptable at this step and is noted for Task 10).

- [ ] **Step 4: Commit**

```bash
git add shared/openapi.json web/src/api/schema.d.ts
git commit -m "chore(web): regenerate OpenAPI + schema types for email-2FA"
```

---

### Task 3: Stand up the web test harness (Vitest + Testing Library)

**Files:**
- Modify: `web/package.json` (devDeps + `test` script)
- Create: `web/vitest.config.ts`
- Create: `web/src/test/setup.ts`
- Create: `web/src/lib/smoke.test.ts` (proves the harness runs)

**Interfaces:**
- Produces: `npm test` runs Vitest in jsdom; Tasks 4, 5, 8 add real tests.

- [ ] **Step 1: Add dev dependencies and the test script**

```bash
cd web && npm i -D vitest@^2 @testing-library/react@^16 @testing-library/jest-dom@^6 @testing-library/user-event@^14 jsdom@^25
```

In `web/package.json` `scripts`, add:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 2: Create the Vitest config**

```ts
// web/vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
```

- [ ] **Step 3: Create the setup file**

```ts
// web/src/test/setup.ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Write a smoke test and run it**

```ts
// web/src/lib/smoke.test.ts
import { describe, expect, it } from "vitest";

describe("harness", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

Run: `cd web && npm test`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add web/package.json web/package-lock.json web/vitest.config.ts web/src/test/setup.ts web/src/lib/smoke.test.ts
git commit -m "test(web): add vitest + testing-library harness"
```

---

### Task 4: API layer — trust-token storage + two-step login

**Files:**
- Modify: `web/src/lib/api.ts`
- Test: `web/src/lib/api.login.test.ts` (create)

**Interfaces:**
- Consumes: generated types `LoginResponse`, `LoginVerifyRequest`, `LoginVerifyResponse`, `ResendRequest`.
- Produces:
  - `trust` storage object: `trust.get(): string | null`, `trust.set(t: string)`, `trust.clear()` (localStorage key `det695.trust`).
  - `type LoginResult = { kind: "authed" } | { kind: "challenge"; challengeToken: string; method: string }`.
  - `api.login(username, password): Promise<LoginResult>` — sends stored `trust_token` in the body; on a `TokenPair`-shaped response stores tokens and returns `{kind:"authed"}`; on a `two_factor_required` response returns `{kind:"challenge", ...}` and stores nothing.
  - `api.loginVerify(challengeToken, code, trustDevice): Promise<void>` — stores the returned tokens; if `trust_token` present, `trust.set(...)`.
  - `api.loginResend(challengeToken): Promise<void>`.

The current `api.login(username, password, totp_code?)` (lines ~139-148) is replaced. The generated `LoginResponse` has optional `access_token`/`refresh_token` plus `two_factor_required`, `method`, `challenge_token`.

- [ ] **Step 1: Write the failing tests**

```ts
// web/src/lib/api.login.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, trust } from "./api";

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => "application/json" },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response);
}

beforeEach(() => {
  localStorage.clear();
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("api.login two-step", () => {
  it("returns authed and stores tokens when backend returns a token pair", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetchOnce(200, { access_token: "a", refresh_token: "r", token_type: "bearer" }),
    );
    const res = await api.login("u", "p");
    expect(res).toEqual({ kind: "authed" });
    expect(localStorage.getItem("det695.access")).toBe("a");
  });

  it("returns a challenge and stores no tokens when 2FA is required", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetchOnce(200, {
        two_factor_required: true,
        method: "email",
        challenge_token: "c123",
        token_type: "bearer",
      }),
    );
    const res = await api.login("u", "p");
    expect(res).toEqual({ kind: "challenge", challengeToken: "c123", method: "email" });
    expect(localStorage.getItem("det695.access")).toBeNull();
  });

  it("sends the stored trust token in the login body", async () => {
    trust.set("T-OKEN");
    const f = mockFetchOnce(200, { access_token: "a", refresh_token: "r", token_type: "bearer" });
    vi.stubGlobal("fetch", f);
    await api.login("u", "p");
    const body = JSON.parse((f.mock.calls[0][1] as RequestInit).body as string);
    expect(body.trust_token).toBe("T-OKEN");
  });

  it("loginVerify stores tokens and persists the trust token", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetchOnce(200, {
        access_token: "a2",
        refresh_token: "r2",
        token_type: "bearer",
        trust_token: "NEWTRUST",
      }),
    );
    await api.loginVerify("c123", "123456", true);
    expect(localStorage.getItem("det695.access")).toBe("a2");
    expect(trust.get()).toBe("NEWTRUST");
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd web && npm test -- api.login`
Expected: FAIL (`api.login` signature/return + `trust` export don't exist yet).

- [ ] **Step 3: Implement**

In `web/src/lib/api.ts`:

Add the trust store near the existing `tokens` object:
```ts
const TRUST_KEY = "det695.trust";
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
```

Add types + rewrite login (types imported from `../api/schema`):
```ts
type LoginResponse = components["schemas"]["LoginResponse"];
type LoginVerifyResponse = components["schemas"]["LoginVerifyResponse"];

export type LoginResult =
  | { kind: "authed" }
  | { kind: "challenge"; challengeToken: string; method: string };

// replaces the previous api.login
async login(username: string, password: string): Promise<LoginResult> {
  const res = await post<LoginResponse>("/auth/login", {
    username,
    password,
    trust_token: trust.get() ?? undefined,
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
  const res = await post<LoginVerifyResponse>("/auth/login/verify", {
    challenge_token: challengeToken,
    code,
    trust_device: trustDevice,
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
  await post("/auth/login/resend", { challenge_token: challengeToken });
},
```

Notes: `post<T>` is the existing generic verb (line ~132). Keep `api.logout()` and `api.me()` unchanged. Do NOT clear the trust token in `logout()`.

- [ ] **Step 4: Run to verify pass**

Run: `cd web && npm test -- api.login && npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/lib/api.login.test.ts
git commit -m "feat(web): two-step login API + trust-token storage"
```

---

### Task 5: API layer — profile 2FA + trusted-device calls

**Files:**
- Modify: `web/src/lib/api.ts`
- Test: `web/src/lib/api.profile2fa.test.ts` (create)

**Interfaces:**
- Consumes: generated `TwoFAStatus`, `TwoFAEnrollRequest`, `TrustedDeviceOut`.
- Produces on `api`:
  - `twoFAStatus(): Promise<TwoFAStatus>` → `GET /profile/2fa/status`
  - `twoFAEnroll(): Promise<void>` → `POST /profile/2fa/enroll` `{method:"email"}`
  - `twoFAEnrollVerify(code): Promise<void>` → `POST /profile/2fa/enroll/verify` `{code}`
  - `twoFAEnrollmentDismiss(): Promise<void>` → `POST /profile/2fa/enrollment-dismiss`
  - `twoFADisable(): Promise<void>` → `POST /profile/2fa/disable`
  - `listTrustedDevices(): Promise<TrustedDeviceOut[]>` → `GET /profile/trusted-devices`
  - `revokeTrustedDevice(id): Promise<void>` → `DELETE /profile/trusted-devices/{id}`
  - `revokeOtherTrustedDevices(): Promise<void>` → `POST /profile/trusted-devices/revoke-others` `{trust_token: trust.get() ?? undefined}`

- [ ] **Step 1: Write the failing tests**

```ts
// web/src/lib/api.profile2fa.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, trust } from "./api";

function mockJson(body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: { get: () => "application/json" },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response);
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("det695.access", "a"); // authed calls attach a bearer
});
afterEach(() => vi.restoreAllMocks());

describe("profile 2fa api", () => {
  it("reads status", async () => {
    vi.stubGlobal("fetch", mockJson({ enabled: true, method: "email", enrollment_prompted: true }));
    const s = await api.twoFAStatus();
    expect(s.enabled).toBe(true);
  });

  it("revoke-others sends the stored trust token", async () => {
    trust.set("MYTRUST");
    const f = mockJson({ detail: "Revoked 1 device(s)" });
    vi.stubGlobal("fetch", f);
    await api.revokeOtherTrustedDevices();
    const body = JSON.parse((f.mock.calls[0][1] as RequestInit).body as string);
    expect(body.trust_token).toBe("MYTRUST");
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd web && npm test -- api.profile2fa`
Expected: FAIL (methods don't exist).

- [ ] **Step 3: Implement** — add the methods to the `api` object using the existing `get`/`post`/`del` verbs. Example bodies:

```ts
type TwoFAStatus = components["schemas"]["TwoFAStatus"];
type TrustedDeviceOut = components["schemas"]["TrustedDeviceOut"];

async twoFAStatus() { return get<TwoFAStatus>("/profile/2fa/status"); },
async twoFAEnroll() { await post("/profile/2fa/enroll", { method: "email" }); },
async twoFAEnrollVerify(code: string) { await post("/profile/2fa/enroll/verify", { code }); },
async twoFAEnrollmentDismiss() { await post("/profile/2fa/enrollment-dismiss", {}); },
async twoFADisable() { await post("/profile/2fa/disable", {}); },
async listTrustedDevices() { return get<TrustedDeviceOut[]>("/profile/trusted-devices"); },
async revokeTrustedDevice(id: number) { await del(`/profile/trusted-devices/${id}`); },
async revokeOtherTrustedDevices() {
  await post("/profile/trusted-devices/revoke-others", { trust_token: trust.get() ?? undefined });
},
```

(Confirm the exact request shapes against `schema.d.ts`; adjust `method` casing/keys to match the generated `TwoFAEnrollRequest`.)

- [ ] **Step 4: Run to verify pass**

Run: `cd web && npm test -- api.profile2fa && npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/lib/api.profile2fa.test.ts
git commit -m "feat(web): profile 2FA + trusted-device API calls"
```

---

### Task 6: Auth context — challenge-aware login

**Files:**
- Modify: `web/src/lib/auth.tsx`

**Interfaces:**
- Consumes: `api.login` (now returns `LoginResult`), `api.loginVerify`, `api.me`.
- Produces on the auth context:
  - `login(username, password): Promise<LoginResult>` — on `{kind:"authed"}` hydrate `user` via `api.me()` and set it; on `{kind:"challenge"}` return it **without** setting a user.
  - `completeVerify(challengeToken, code, trustDevice): Promise<void>` — calls `api.loginVerify`, then `api.me()`, then `setUser`.

- [ ] **Step 1: Update the context type and implementation**

In `src/lib/auth.tsx`, change `login` to return `LoginResult` (import the type from `./api`) and add `completeVerify`:

```tsx
const login = async (username: string, password: string): Promise<LoginResult> => {
  const res = await api.login(username, password);
  if (res.kind === "authed") {
    setUser(await api.me());
  }
  return res;
};

const completeVerify = async (
  challengeToken: string,
  code: string,
  trustDevice: boolean,
): Promise<void> => {
  await api.loginVerify(challengeToken, code, trustDevice);
  setUser(await api.me());
};
```

Add `completeVerify` to the `AuthState` type and the context `value`.

- [ ] **Step 2: Verify it compiles**

Run: `cd web && npm run build`
Expected: PASS (a type error in `Login.tsx` is expected here because its `await login(...)` no longer matches — fixed in Task 7; if the build blocks, proceed to Task 7 in the same fix cycle).

- [ ] **Step 3: Commit**

```bash
git add web/src/lib/auth.tsx
git commit -m "feat(web): challenge-aware login + completeVerify in auth context"
```

---

### Task 7: Login page — route to the verify screen on a challenge

**Files:**
- Modify: `web/src/pages/Login.tsx`

**Interfaces:**
- Consumes: `useAuth().login` (returns `LoginResult`), `useNavigate`.
- Produces: on `{kind:"challenge"}`, navigate to `/login/verify` passing `challengeToken`/`method` via router state; on `{kind:"authed"}`, navigate to `/dashboard`.

Remove the `needs2fa`/`totp` state and the inline TOTP `<input>` (lines ~17-18, 115-129) and the 401 message-sniffing branch.

- [ ] **Step 1: Rewrite the submit handler and drop the TOTP field**

```tsx
async function onSubmit(e: FormEvent) {
  e.preventDefault();
  setError(null);
  setBusy(true);
  try {
    const res = await login(username, password);
    if (res.kind === "challenge") {
      navigate("/login/verify", {
        replace: true,
        state: { challengeToken: res.challengeToken, method: res.method },
      });
      return;
    }
    navigate("/dashboard", { replace: true });
  } catch (err) {
    if (err instanceof ApiError) {
      setError(err.message || "Sign-in failed. Check your credentials.");
    } else {
      setError("Unable to reach the server. Try again.");
    }
  } finally {
    setBusy(false);
  }
}
```

Delete the `{needs2fa && (...)}` block and the `needs2fa`/`totp` `useState`s.

- [ ] **Step 2: Verify**

Run: `cd web && npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Login.tsx
git commit -m "feat(web): route to verify screen on 2FA challenge; remove inline TOTP field"
```

---

### Task 8: The verify screen + route

**Files:**
- Create: `web/src/pages/LoginVerify.tsx`
- Modify: `web/src/main.tsx` (add `/login/verify` as a sibling of `/login`)
- Test: `web/src/pages/LoginVerify.test.tsx` (create)

**Interfaces:**
- Consumes: `useAuth().completeVerify`, `api.loginResend`, router `location.state`.
- Produces: `/login/verify` route rendering code entry + resend (60s countdown) + "Trust this device for 30 days" checkbox; on success → `/dashboard`; if reached with no challenge state → redirect to `/login`.

- [ ] **Step 1: Write the failing component test**

```tsx
// web/src/pages/LoginVerify.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { LoginVerify } from "./LoginVerify";

const completeVerify = vi.fn().mockResolvedValue(undefined);
vi.mock("../lib/auth", () => ({
  useAuth: () => ({ completeVerify }),
}));
vi.mock("../lib/api", () => ({ api: { loginResend: vi.fn().mockResolvedValue(undefined) } }));

function renderAt(state: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/login/verify", state }]}>
      <Routes>
        <Route path="/login/verify" element={<LoginVerify />} />
        <Route path="/dashboard" element={<div>DASH</div>} />
        <Route path="/login" element={<div>LOGIN</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LoginVerify", () => {
  it("redirects to /login when there is no challenge", () => {
    renderAt(undefined);
    expect(screen.getByText("LOGIN")).toBeInTheDocument();
  });

  it("submits the code and trust flag, then lands on dashboard", async () => {
    renderAt({ challengeToken: "c1", method: "email" });
    await userEvent.type(screen.getByLabelText(/code/i), "123456");
    await userEvent.click(screen.getByLabelText(/trust this device/i));
    await userEvent.click(screen.getByRole("button", { name: /verify/i }));
    expect(completeVerify).toHaveBeenCalledWith("c1", "123456", true);
    expect(await screen.findByText("DASH")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd web && npm test -- LoginVerify`
Expected: FAIL (component doesn't exist).

- [ ] **Step 3: Implement the screen**

```tsx
// web/src/pages/LoginVerify.tsx
import { FormEvent, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError, api } from "../lib/api";
import { useAuth } from "../lib/auth";

type ChallengeState = { challengeToken?: string; method?: string };

export function LoginVerify() {
  const { completeVerify } = useAuth();
  const navigate = useNavigate();
  const state = (useLocation().state ?? {}) as ChallengeState;
  const challengeToken = state.challengeToken;

  const [code, setCode] = useState("");
  const [trustDevice, setTrustDevice] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!challengeToken) navigate("/login", { replace: true });
  }, [challengeToken, navigate]);

  useEffect(() => {
    if (cooldown <= 0) return;
    timer.current = window.setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [cooldown]);

  if (!challengeToken) return null;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await completeVerify(challengeToken as string, code.trim(), trustDevice);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "Verification failed. Try again.";
      setError(msg || "Verification failed. Try again.");
      // If the challenge was invalidated (too many attempts), send them back.
      if (err instanceof ApiError && err.status === 400) {
        setTimeout(() => navigate("/login", { replace: true }), 1500);
      }
    } finally {
      setBusy(false);
    }
  }

  async function onResend() {
    setError(null);
    try {
      await api.loginResend(challengeToken as string);
      setCooldown(60);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resend the code.");
    }
  }

  return (
    <div className="card" style={{ maxWidth: 420, margin: "10vh auto" }}>
      <h1>Enter your sign-in code</h1>
      <p className="muted">
        We emailed a 6-digit code to your address. It expires in 10 minutes.
      </p>
      <form onSubmit={onSubmit}>
        <label className="field-label" htmlFor="code">
          Verification code
        </label>
        <input
          id="code"
          className="input"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          autoFocus
        />
        <label style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <input
            type="checkbox"
            checked={trustDevice}
            onChange={(e) => setTrustDevice(e.target.checked)}
          />
          Trust this device for 30 days
        </label>
        {error && <div className="form-error">{error}</div>}
        <button className="btn btn-primary" type="submit" disabled={busy || code.length < 6}>
          {busy ? "Verifying…" : "Verify"}
        </button>
      </form>
      <button className="btn btn-ghost" onClick={onResend} disabled={cooldown > 0}>
        {cooldown > 0 ? `Resend code (${cooldown}s)` : "Resend code"}
      </button>
    </div>
  );
}
```

In `web/src/main.tsx`, add the route as a sibling of `/login` (NOT under `RequireAuth`, and wrapped like `/login` is — but do NOT wrap in `RedirectIfAuthed`, since the user has valid creds but no session yet):

```tsx
<Route path="/login/verify" element={<LoginVerify />} />
```

(Place it right after the `/login` route; import `LoginVerify` at the top.)

- [ ] **Step 4: Run to verify pass**

Run: `cd web && npm test -- LoginVerify && npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/LoginVerify.tsx web/src/main.tsx web/src/pages/LoginVerify.test.tsx
git commit -m "feat(web): email-2FA verify screen with resend countdown + trust toggle"
```

---

### Task 9: First-login enrollment prompt (one-time modal)

**Files:**
- Create: `web/src/components/EnrollmentPrompt.tsx`
- Modify: `web/src/components/AppShell.tsx` (mount the prompt)

**Interfaces:**
- Consumes: `useAuth().user`, `api.twoFAEnroll`, `api.twoFAEnrollVerify`, `api.twoFAEnrollmentDismiss`, `api.me` (to refresh the user after enroll/dismiss).
- Produces: a modal shown once when `user && !user.two_factor_enabled && !user.two_factor_enrollment_prompted`. "Enable now" → enroll → code entry → verify → refresh user + close. "Not now" → dismiss → refresh user + close.

- [ ] **Step 1: Implement the prompt**

Model it on the `TwoFactorCard` mutation/toast pattern. It has two internal steps: `intro` (Enable now / Not now) and `verify` (code entry). After enroll succeeds move to `verify`; after enroll-verify or dismiss succeeds, refresh the auth user (call a new `refresh()` on the context OR re-run `api.me()` and update context) and close. Add a `refresh(): Promise<void>` to the auth context that does `setUser(await api.me())` if one does not already exist.

Gate rendering:
```tsx
const { user } = useAuth();
const [open, setOpen] = useState(false);
useEffect(() => {
  if (user && !user.two_factor_enabled && !user.two_factor_enrollment_prompted) setOpen(true);
}, [user]);
if (!open || !user) return null;
```

- [ ] **Step 2: Mount it in `AppShell`** so it appears on the first authenticated screen:

```tsx
// inside AppShell's returned tree, after the main content
<EnrollmentPrompt />
```

- [ ] **Step 3: Verify**

Run: `cd web && npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/EnrollmentPrompt.tsx web/src/components/AppShell.tsx web/src/lib/auth.tsx
git commit -m "feat(web): one-time first-login 2FA enrollment prompt"
```

---

### Task 10: Profile — email-2FA card + Trusted Devices card

**Files:**
- Modify: `web/src/pages/Profile.tsx` (replace `TwoFactorCard`, lines ~282-429; add `TrustedDevicesCard`)

**Interfaces:**
- Consumes: `api.twoFAStatus`, `api.twoFAEnroll`, `api.twoFAEnrollVerify`, `api.twoFADisable`, `api.listTrustedDevices`, `api.revokeTrustedDevice`, `api.revokeOtherTrustedDevices`, `trust`.
- Produces: an email-2FA enable/disable card (enable = enroll → test code → verify; disable = confirm → disable) and a Trusted Devices card (list with label/last-used/expires, per-row revoke, "revoke all others").

- [ ] **Step 1: Rewrite `TwoFactorCard` for email 2FA**

Replace the TOTP secret/otpauth UI with:
- Read `api.twoFAStatus()` (`["profile-2fa"]`).
- If disabled: an "Enable email 2FA" button → `twoFAEnroll()` → reveal a 6-digit code input → `twoFAEnrollVerify(code)` → invalidate `["profile-2fa"]` + `["profile"]`.
- If enabled: show "Email 2FA is on" + a "Turn off" button → `twoFADisable()` (note in copy that this also signs out trusted devices) → invalidate.

Keep the existing `useMutation`/`notify` pattern; reuse the code-input UX from the old card.

- [ ] **Step 2: Add `TrustedDevicesCard`**

```tsx
function TrustedDevicesCard() {
  const qc = useQueryClient();
  const devicesQ = useQuery({
    queryKey: ["trusted-devices"],
    queryFn: () => api.listTrustedDevices(),
  });
  const revoke = useMutation({
    mutationFn: (id: number) => api.revokeTrustedDevice(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trusted-devices"] }),
  });
  const revokeOthers = useMutation({
    mutationFn: () => api.revokeOtherTrustedDevices(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trusted-devices"] }),
  });
  const devices = devicesQ.data ?? [];
  return (
    <section className="card">
      <h2>Trusted devices</h2>
      {devices.length === 0 ? (
        <p className="muted">No trusted devices.</p>
      ) : (
        <ul>
          {devices.map((d) => (
            <li key={d.id}>
              {d.device_label} — last used {new Date(d.last_used_at).toLocaleString()} — expires{" "}
              {new Date(d.expires_at).toLocaleDateString()}
              <button className="btn btn-ghost" onClick={() => revoke.mutate(d.id)}>
                Revoke
              </button>
            </li>
          ))}
        </ul>
      )}
      {devices.length > 1 && (
        <button className="btn btn-ghost" onClick={() => revokeOthers.mutate()}>
          Revoke all other devices
        </button>
      )}
    </section>
  );
}
```

Render `<TrustedDevicesCard />` in the Profile page's card stack (near line ~70-72), ideally only when 2FA is enabled.

- [ ] **Step 3: Verify**

Run: `cd web && npm run build && npm run lint`
Expected: PASS (this also clears any temporary `TwoFAStatus` type mismatch from Task 2).

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/Profile.tsx
git commit -m "feat(web): email-2FA enable/disable + trusted-device management in Profile"
```

---

### Task 11: Admin — 2FA toggle + revoke trusted devices

**Files:**
- Modify: `web/src/pages/Admin.tsx`

**Interfaces:**
- Consumes: `PATCH /admin/users/:id` (`AdminUserUpdate.two_factor_enabled`), `POST /admin/users/:id/revoke-trusted-devices`.
- Produces: in the user row/drawer, a 2FA on/off control (mirrors the `is_active` `stateChip` toggle, sending `{two_factor_enabled}` via the existing `update` mutation) and a "Revoke trusted devices" action (mirrors the `unlock` pattern) calling the admin revoke endpoint.

- [ ] **Step 1: Add the admin revoke call to the api client**

In `src/lib/api.ts`, add:
```ts
async adminRevokeTrustedDevices(userId: number) {
  await post(`/admin/users/${userId}/revoke-trusted-devices`, {});
},
```

- [ ] **Step 2: Add the toggle + action in `Admin.tsx`**

- 2FA toggle: reuse the `stateChip`/active-toggle pattern (lines ~213-225) but send `{ two_factor_enabled: next }` through the existing `update` mutation (lines ~166-170). Label reflects `user.two_factor_enabled`.
- Revoke action: add a button in the row actions or `EditUserDrawer` (near the unlock block) → `useMutation(api.adminRevokeTrustedDevices)` → `onSuccess` invalidate `["admin-users"]` + toast the returned count.

- [ ] **Step 3: Verify**

Run: `cd web && npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web/src/lib/api.ts web/src/pages/Admin.tsx
git commit -m "feat(web): admin 2FA enable/disable + revoke trusted devices"
```

---

## Final verification

- [ ] `cd backend && uv run pytest -q` — backend still green (Task 1 addition included).
- [ ] `cd web && npm test` — all Vitest tests pass.
- [ ] `cd web && npm run build && npm run lint` — types + oxlint clean.
- [ ] Manual smoke (documented, not automated — requires the backend running on :8099): enable 2FA in Profile → log out → log in → verify screen appears, code from email works, "trust this device" → next login skips the code; Profile lists the trusted device and can revoke it; admin can toggle 2FA and revoke a user's devices; a fresh un-prompted user sees the enrollment modal once.

## Spec coverage check

- Verify screen (code + resend + countdown + trust toggle) → Tasks 7, 8. First-login ask-once enrollment → Task 9. Profile email-2FA enable/disable (enroll→test-code→verify) → Task 10. Trusted-devices list/revoke/revoke-others → Tasks 5, 10 (+ Task 1 backend for cookieless current-device preservation). Admin toggle + revoke → Task 11. Two-step login + trust-token transport → Tasks 4, 6. API contract → Task 2. Test harness → Task 3.
- **Cookieless trust transport (RULING):** trust token in localStorage + login body (not cookie). **Test harness (RULING):** new Vitest+RTL. **Backend touch (RULING):** `revoke-others` gains an optional body token (Task 1).
- **Out of scope:** iOS client (its own plan); active TOTP; SMS; backup codes.
