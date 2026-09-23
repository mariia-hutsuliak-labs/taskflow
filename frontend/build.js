const fs = require("node:fs");
const path = require("node:path");

const SRC = __dirname;
const DIST = path.join(SRC, "dist");
const FILES = ["index.html", "style.css", "app.js", "utils.js"];
const GENERATED_AT_RUNTIME = ["config.js"];

const html = fs.readFileSync(path.join(SRC, "index.html"), "utf8");
const referenced = [...html.matchAll(/(?:src|href)="([^"]+)"/g)].map((m) => m[1]);

const missing = referenced.filter(
  (ref) => !GENERATED_AT_RUNTIME.includes(ref) && !fs.existsSync(path.join(SRC, ref))
);
if (missing.length > 0) {
  console.error("Build failed, index.html references missing files:", missing);
  process.exit(1);
}

fs.rmSync(DIST, { recursive: true, force: true });
fs.mkdirSync(DIST);
for (const file of FILES) {
  fs.copyFileSync(path.join(SRC, file), path.join(DIST, file));
}
console.log(`Build OK: ${FILES.length} files copied to dist/`);