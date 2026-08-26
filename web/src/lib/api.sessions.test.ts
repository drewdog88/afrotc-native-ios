import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

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

describe("sessions api", () => {
  it("lists sessions", async () => {
    const rows = [
      {
        id: 1,
        device_label: "Chrome on macOS",
        current: true,
        created_at: "x",
        last_seen_at: "x",
        expires_at: "x",
        ip_address: null,
      },
    ];
    vi.stubGlobal("fetch", mockJson(rows));
    const out = await api.listSessions();
    expect(out[0].current).toBe(true);
    expect((global.fetch as any).mock.calls[0][0]).toContain("/profile/sessions");
  });

  it("revokes a session with DELETE", async () => {
    vi.stubGlobal("fetch", mockJson({ detail: "ok" }));
    await api.revokeSession(5);
    const [url, opts] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/profile/sessions/5");
    expect(opts.method).toBe("DELETE");
  });

  it("revokes others with POST", async () => {
    vi.stubGlobal("fetch", mockJson({ detail: "ok" }));
    await api.revokeOtherSessions();
    const [url, opts] = (global.fetch as any).mock.calls[0];
    expect(url).toContain("/profile/sessions/revoke-others");
    expect(opts.method).toBe("POST");
  });
});
