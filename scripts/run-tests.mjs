import { spawnSync } from "node:child_process";
import { readdirSync, realpathSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const TYPESCRIPT_TESTS = [
  "src/lib/app-data/app-data.test.ts",
  "src/lib/auth/gate-identity.test.ts",
  "src/lib/grok-contract.test.ts",
  "src/lib/completion-history.test.ts",
];

// Pass real filenames directly to Node. Shell glob quoting differs between
// Windows and POSIX, and an unmatched literal can report a zero-test success.
export function discoverScriptTests(root) {
  const found = [];
  function visit(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) visit(path);
      else if (entry.isFile() && entry.name.endsWith(".test.mjs")) found.push(path);
    }
  }
  visit(join(root, "scripts"));
  if (found.length === 0) throw new Error("No script tests discovered");
  return found.sort();
}

export function runTests(root, spawn = spawnSync) {
  const scripts = discoverScriptTests(root);
  const typed = TYPESCRIPT_TESTS.map((path) => {
    const fullPath = join(root, path);
    if (!statSync(fullPath).isFile()) throw new Error(`Not a test file: ${path}`);
    return fullPath;
  });
  for (const args of [
    ["--test", ...scripts],
    ["--experimental-strip-types", "--test", ...typed],
  ]) {
    const result = spawn(process.execPath, args, {
      cwd: root,
      stdio: "inherit",
      shell: false,
    });
    if (result.error) throw result.error;
    if (result.signal || !Number.isInteger(result.status) || result.status < 0) {
      throw new Error(`Test process did not complete: ${result.signal ?? "unknown status"}`);
    }
    if (result.status !== 0) return result.status;
  }
  return 0;
}

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
if (process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))) {
  try {
    process.exitCode = runTests(ROOT);
  } catch (error) {
    console.error(`Test runner failed: ${error.message}`);
    process.exitCode = 1;
  }
}
