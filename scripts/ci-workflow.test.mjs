import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const ci = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../.github/workflows/ci.yml"),
  "utf8",
);

test("CI typechecks every Node matrix leg without silencing or skipping the gate", () => {
  assert.match(ci, /node-version: \["22", "24"\]/);
  assert.match(ci, /run: npm run typecheck/);
  assert.doesNotMatch(ci, /continue-on-error|ignoreDeprecations/);
  const typecheck = ci.slice(ci.indexOf("Typecheck application contracts"), ci.indexOf("Lint source"));
  assert.doesNotMatch(typecheck, /\bif:/);
});
