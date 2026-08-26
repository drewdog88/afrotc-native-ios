import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, trust } from "./api";

// localStorage polyfill for the Node/jsdom toolchain lives in src/test/setup.ts.

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
