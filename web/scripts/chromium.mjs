// Resolve a usable Chromium binary from the Playwright browser cache, robust to
// version bumps and the platform folder/app rename (chrome-mac → chrome-mac-arm64,
// "Chromium.app" → "Google Chrome for Testing.app", plus the headless shell).
// Scans every installed build and returns the newest match, so the shot scripts
// keep working after `npx playwright install` pulls a new revision.
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";

const CACHE = `${process.env.HOME}/Library/Caches/ms-playwright`;

// Per-build relative paths to try, most-preferred first (full browser, then the
// headless shell as a fallback — screenshots work fine with either).
const REL = [
  ["chrome-mac-arm64", "Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing"],
  ["chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium"],
  ["chrome-headless-shell-mac-arm64", "chrome-headless-shell"],
  ["chrome-headless-shell-mac-x64", "chrome-headless-shell"],
];

export function findChromium() {
  let dirs = [];
  try {
    dirs = readdirSync(CACHE).filter((d) => d.startsWith("chromium"));
  } catch {
    throw new Error(`No Playwright cache at ${CACHE} — run: npx playwright install chromium`);
  }
  // Newest revision first (numeric suffix descending).
  dirs.sort((a, b) => (Number(b.split("-").pop()) || 0) - (Number(a.split("-").pop()) || 0));

  for (const dir of dirs) {
    for (const rel of REL) {
      const p = join(CACHE, dir, ...rel);
      if (existsSync(p)) return p;
    }
  }
  throw new Error("No Chromium binary found in Playwright cache — run: npx playwright install chromium");
}
