import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const preview = readFileSync(join(root, "src/lib/auth/preview.ts"), "utf8");
const server = readFileSync(join(root, "src/lib/auth/server.ts"), "utf8");

test("preview.ts no longer exports a baked-in client secret", () => {
  assert.doesNotMatch(preview, /export const PREVIEW_CLIENT_SECRET/);
});

test("server.ts reads GROK_AUTH_CLIENT_SECRET from the environment with no fallback", () => {
  assert.match(server, /env\("GROK_AUTH_CLIENT_SECRET"\)/);
  assert.doesNotMatch(server, /PREVIEW_CLIENT_SECRET/);
  assert.doesNotMatch(server, /\?\?\s*PREVIEW_CLIENT_SECRET/);
});
