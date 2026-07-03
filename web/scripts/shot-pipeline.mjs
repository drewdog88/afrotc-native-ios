// Focused capture of the Pipeline trend chart — plain view + a hovered state,
// so we can eyeball the trend line geometry and end-labels before/after a change.
import { chromium } from "playwright-core";
import { existsSync, mkdirSync } from "node:fs";

const CANDIDATES = [
  `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1223/chrome-mac/Chromium.app/Contents/MacOS/Chromium`,
  `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1217/chrome-mac/Chromium.app/Contents/MacOS/Chromium`,
  `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1208/chrome-mac/Chromium.app/Contents/MacOS/Chromium`,
  `${process.env.HOME}/Library/Caches/ms-playwright/chromium-1187/chrome-mac/Chromium.app/Contents/MacOS/Chromium`,
];
const executablePath = CANDIDATES.find((p) => existsSync(p));
if (!executablePath) throw new Error("No bundled Chromium found");

const BASE = process.env.APP_URL ?? "http://127.0.0.1:5173";
const OUT = "shots";
const TAG = process.env.TAG ?? "before";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const errs = [];
page.on("console", (m) => m.type() === "error" && errs.push(m.text()));
page.on("pageerror", (e) => errs.push(String(e)));

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill("#username", "admin");
await page.fill("#password", "Det695Demo!");
await page.click('button[type="submit"]');
await page.waitForURL("**/dashboard", { timeout: 8000 });

await page.goto(`${BASE}/pipeline`, { waitUntil: "networkidle" });
await page.waitForTimeout(1000);
await page.screenshot({ path: `${OUT}/pipeline-${TAG}.png`, fullPage: true });

// Hover the middle of the chart to capture the crosshair + tooltip.
const svg = await page.$("svg[aria-label^='Cumulative']");
if (svg) {
  const box = await svg.boundingBox();
  await page.mouse.move(box.x + box.width * 0.55, box.y + box.height * 0.4);
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/pipeline-${TAG}-hover.png`, fullPage: true });
}

console.log(errs.length ? `ERRORS:\n${errs.join("\n")}` : "clean");
await browser.close();
