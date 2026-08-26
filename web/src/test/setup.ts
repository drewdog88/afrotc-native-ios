import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Node 22+'s built-in `localStorage` global collides with jsdom's window shim:
// without a `--localstorage-file` path, Node's native Storage stub is a frozen,
// method-less object, so jsdom's window.localStorage (which delegates to it) has
// no getItem/setItem/clear on this toolchain (observed on Node 25 + jsdom 25).
// Install a working in-memory Storage globally so any test touching localStorage
// (login/trust, Profile 2FA, etc.) behaves normally.
function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => {
      store.set(k, String(v));
    },
    removeItem: (k: string) => {
      store.delete(k);
    },
    clear: () => {
      store.clear();
    },
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size;
    },
  } as Storage;
}

if (typeof localStorage === "undefined" || typeof localStorage.clear !== "function") {
  vi.stubGlobal("localStorage", createMemoryStorage());
}
