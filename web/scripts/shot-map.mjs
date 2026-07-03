import { chromium } from "playwright-core";
import { findChromium } from "./chromium.mjs";
const executablePath = findChromium();
const BASE = process.env.APP_URL ?? "http://127.0.0.1:5173";
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
await page.goto(`${BASE}/map`, { waitUntil: "networkidle" });
await page.waitForTimeout(2500); // let tiles + fitBounds settle
await page.screenshot({ path: "shots/screen-map.png", fullPage: false });
// also click the first list row if present, to exercise the popup
const row = page.locator('button:has-text("")').first();
console.log("map errors:", errs.length ? errs.slice(0, 6) : "clean");
await browser.close();
