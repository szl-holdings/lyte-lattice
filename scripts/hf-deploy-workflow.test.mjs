import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const WORKFLOW = readFileSync(join(ROOT, ".github/workflows/hf-deploy.yml"), "utf8");

function eventBlock(name) {
  const match = WORKFLOW.match(
    new RegExp(String.raw`\n  ${name}:\n([\s\S]*?)(?=\n  [A-Za-z_][A-Za-z0-9_-]*:|\npermissions:)`),
  );
  assert.ok(match, `missing ${name} event block`);
  return match[1];
}

test("every main update schedules read-only ownership verification", () => {
  const push = eventBlock("push");
  assert.match(push, /^ {4}branches: \[main\]$/m);
  assert.doesNotMatch(push, /^ {4}paths(?:-ignore)?:/m);
  assert.match(WORKFLOW, /^permissions:\n {2}contents: read$/m);
  assert.match(WORKFLOW, /run: python -I source\/scripts\/test_hf_ownership\.py/);
  assert.match(WORKFLOW, /python -I source\/scripts\/verify-hf-ownership\.py/);
  assert.match(WORKFLOW, /--source source --governance governance --publisher publisher/);
  assert.match(WORKFLOW, /repository: szl-holdings\/a11oy/);
  assert.doesNotMatch(WORKFLOW, /reusable-hf-deploy\.yml|require-default-branch-tip|\bHF_[A-Z_]+\b/);
  assert.doesNotMatch(WORKFLOW, /\b(?:upload_folder|upload_file|create_repo|restart_space|pause_space)\s*\(/);
});

test("live ownership read uses the Actions token and offline steps do not", () => {
  const liveAt = WORKFLOW.indexOf("Verify actual ownership and record the exact inspected commits");
  assert.ok(liveAt > 0);
  const live = WORKFLOW.slice(liveAt, WORKFLOW.indexOf("Preserve the source-authority receipt"));
  const offline = WORKFLOW.slice(0, liveAt);
  assert.match(live, /GITHUB_TOKEN: \$\{\{ github\.token \}\}/);
  assert.doesNotMatch(offline, /GITHUB_TOKEN|secrets\./);
  assert.doesNotMatch(WORKFLOW, /secrets\.|HF_TOKEN|HUGGING_FACE/);
});

test("pull request validation remains narrowly path-scoped", () => {
  const pullRequest = eventBlock("pull_request");
  assert.match(pullRequest, /^ {4}branches: \[main\]$/m);
  assert.match(pullRequest, /^ {4}paths:$/m);
});
