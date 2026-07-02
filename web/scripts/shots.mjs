// Drive the running dev server with a bundled Chromium and capture prototype
// screenshots (login + dashboard). Uses playwright-core against an existing
// browser build so nothing needs downloading.
import { chromium } from "playwright-core";
import { existsSync } from "node:fs";
import { mkdirSync } from "node:fs";

const CANDIDATES = [
  `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1187/chrome-mac/Chromium.app/Contents/MacOS/Chromium`,
  `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1169/chrome-mac/Chromium.app/Contents/MacOS/Chromium`,
];
const executablePath = CANDIDATES.find((p) => existsSync(p));
if (!executablePath) throw new Error("No bundled Chromium found");

const BASE = process.env.APP_URL ?? "http://localhost:5173";
const OUT = "shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("pageerror", (e) => errors.push(String(e)));

// Login screen
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/01-login.png` });

// Sign in
await page.fill("#username", "admin");
await page.fill("#password", "Det695Demo!");
await page.click('button[type="submit"]');
await page.waitForURL("**/dashboard", { timeout: 8000 });
await page.waitForTimeout(1200); // let queries settle + funnel animate
await page.screenshot({ path: `${OUT}/02-dashboard.png` });

// Hover the trend chart to show the tooltip/crosshair
const svg = page.locator("svg[aria-label='New recruits over time']");
if (await svg.count()) {
  const box = await svg.boundingBox();
  if (box) await page.mouse.move(box.x + box.width * 0.62, box.y + box.height * 0.5);
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/03-dashboard-hover.png` });
}

// Dark mode
await page.emulateMedia({ colorScheme: "dark" });
await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
await page.waitForTimeout(400);
await page.screenshot({ path: `${OUT}/04-dashboard-dark.png` });

console.log(errors.length ? `CONSOLE ERRORS:\n${errors.join("\n")}` : "No console errors.");
await browser.close();
