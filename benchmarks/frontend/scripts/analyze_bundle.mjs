#!/usr/bin/env node
/**
 * Dependency-free bundle analyzer for finance-tracker frontend.
 *
 * Reads ../../frontend/dist/assets/*.js (and .css), gzips each in memory
 * using Node's built-in zlib, sums sizes, and emits a JSON summary.
 *
 * Works regardless of Vite config: minified or not, manifest.json present
 * or not, sourcemaps shipped or not.
 *
 * Output JSON shape:
 * {
 *   "generatedAt": ISO,
 *   "frontendDist": absolute path,
 *   "manifestPresent": bool,
 *   "totals": { rawBytes, gzBytes, jsRawBytes, jsGzBytes, cssRawBytes, cssGzBytes },
 *   "budgets": { jsGzipKB350: { budgetBytes, actualBytes, withinBudget } },
 *   "chunks": [{ file, kind, rawBytes, gzBytes, routeHint }]
 * }
 */

import { readdirSync, readFileSync, statSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { dirname, join, resolve, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const HARNESS_DIR = resolve(__dirname, '..');
const FRONTEND_DIR = resolve(HARNESS_DIR, '..', '..', 'frontend');
const DIST_DIR = resolve(FRONTEND_DIR, 'dist');
const ASSETS_DIR = resolve(DIST_DIR, 'assets');
const MANIFEST_PATH = resolve(DIST_DIR, '.vite', 'manifest.json');

const OUTPUT_PATH = process.env.BUNDLE_OUTPUT
  || resolve(HARNESS_DIR, 'reports', 'latest', 'bundle-summary.json');

const JS_GZ_BUDGET_BYTES = 350 * 1024;

function fail(msg) {
  console.error(`analyze_bundle: ${msg}`);
  process.exit(1);
}

if (!existsSync(DIST_DIR)) {
  fail(`frontend/dist/ not found at ${DIST_DIR}. Build the frontend first.`);
}
if (!existsSync(ASSETS_DIR)) {
  fail(`frontend/dist/assets/ not found at ${ASSETS_DIR}. Build the frontend first.`);
}

/** Walk a dir recursively, return absolute file paths. */
function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (entry.isFile()) out.push(full);
  }
  return out;
}

/**
 * Best-effort route hint: Vite emits chunks like `Dashboard-abc123.js` when
 * code splitting is on, or a single `index-abc123.js` when not. Strip the
 * 8-char hash + extension; if the leftover looks like a known page or a
 * vendor name, surface it. Otherwise label as 'main'.
 */
function routeHintFromName(name) {
  const stem = basename(name, extname(name));
  // Vite default pattern: "<name>-<hash>". Hash is typically 8+ hex chars.
  const m = stem.match(/^(.*?)-[A-Za-z0-9_-]{8,}$/);
  const cleaned = (m ? m[1] : stem).toLowerCase();
  if (!cleaned || cleaned === 'index' || cleaned === 'main') return 'main';
  if (cleaned.includes('vendor')) return 'vendor';
  if (cleaned.includes('chunk')) return 'shared';
  return cleaned;
}

const files = walk(ASSETS_DIR).filter((f) => /\.(js|css|mjs)$/i.test(f));

const chunks = [];
let jsRaw = 0, jsGz = 0, cssRaw = 0, cssGz = 0;

for (const filePath of files) {
  const buf = readFileSync(filePath);
  const gzBuf = gzipSync(buf, { level: 9 });
  const ext = extname(filePath).toLowerCase();
  const kind = ext === '.css' ? 'css' : 'js';
  if (kind === 'js') { jsRaw += buf.length; jsGz += gzBuf.length; }
  else { cssRaw += buf.length; cssGz += gzBuf.length; }

  chunks.push({
    file: filePath.slice(DIST_DIR.length + 1),
    kind,
    rawBytes: buf.length,
    gzBytes: gzBuf.length,
    routeHint: routeHintFromName(filePath),
  });
}

chunks.sort((a, b) => b.gzBytes - a.gzBytes);

const summary = {
  generatedAt: new Date().toISOString(),
  frontendDist: DIST_DIR,
  manifestPresent: existsSync(MANIFEST_PATH),
  manifestPath: existsSync(MANIFEST_PATH) ? MANIFEST_PATH : null,
  totals: {
    rawBytes: jsRaw + cssRaw,
    gzBytes: jsGz + cssGz,
    jsRawBytes: jsRaw,
    jsGzBytes: jsGz,
    cssRawBytes: cssRaw,
    cssGzBytes: cssGz,
    chunkCount: chunks.length,
  },
  budgets: {
    jsGzipKB350: {
      budgetBytes: JS_GZ_BUDGET_BYTES,
      actualBytes: jsGz,
      withinBudget: jsGz <= JS_GZ_BUDGET_BYTES,
    },
  },
  chunks,
};

mkdirSync(dirname(OUTPUT_PATH), { recursive: true });
writeFileSync(OUTPUT_PATH, JSON.stringify(summary, null, 2));

// Try to keep stat() lint quiet on unused import
void statSync;

console.log(`analyze_bundle: ${chunks.length} chunks; JS ${(jsGz / 1024).toFixed(1)} KB gz / ${(jsRaw / 1024).toFixed(1)} KB raw`);
console.log(`analyze_bundle: wrote ${OUTPUT_PATH}`);
