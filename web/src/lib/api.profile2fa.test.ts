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
