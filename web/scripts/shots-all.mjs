// Drive the running dev server through every screen, capture a screenshot per
// route, and collect console/page errors per route. This is the runtime smoke
// test the typecheck can't give us — a screen that mounts with a thrown error
// shows up here even though it compiled.
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";
import { findChromium } from "./chromium.mjs";

const executablePath = findChromium();

const BASE = process.env.APP_URL ?? "http://127.0.0.1:5173";
const OUT = "shots";
mkdirSync(OUT, { recursive: true });

const ROUTES = [
  ["recruits", "/recruits"],
  ["cadets", "/cadets"],
  ["contacts", "/contacts"],
  ["events", "/events"],
  ["follow-ups", "/follow-ups"],
  ["pipeline", "/pipeline"],
  ["materials", "/materials"],
  ["import", "/import"],
  ["profile", "/profile"],
  ["admin", "/admin"],
];

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });

let bucket = [];
page.on("console", (m) => m.type() === "error" && bucket.push(m.text()));
page.on("pageerror", (e) => bucket.push(String(e)));

// Sign in first.
await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.fill("#username", "admin");
await page.fill("#password", "Det695Demo!");
await page.click('button[type="submit"]');
await page.waitForURL("**/dashboard", { timeout: 8000 });
await page.waitForTimeout(800);

const report = {};
for (const [name, path] of ROUTES) {
  bucket = [];
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${OUT}/screen-${name}.png`, fullPage: true });
  report[name] = [...bucket];
}

console.log("=== per-route console/page errors ===");
let clean = true;
for (const [name] of ROUTES) {
  const errs = report[name] ?? [];
  if (errs.length) {
    clean = false;
    console.log(`\n[${name}] ${errs.length} error(s):`);
    for (const e of errs.slice(0, 6)) console.log("   " + e.replace(/\s+/g, " ").slice(0, 300));
  } else {
    console.log(`[${name}] clean`);
  }
}
console.log(clean ? "\nALL ROUTES CLEAN" : "\nSOME ROUTES HAD ERRORS");
await browser.close();
