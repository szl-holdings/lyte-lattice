import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { discoverScriptTests, runTests, TYPESCRIPT_TESTS } from "./run-tests.mjs";

function workspace(t) {
  const root = mkdtempSync(join(tmpdir(), "lyte test runner "));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  mkdirSync(join(root, "scripts"));
  return root;
}

function write(root, path, body) {
  const fullPath = join(root, path);
  mkdirSync(dirname(fullPath), { recursive: true });
  writeFileSync(fullPath, body);
}

function completeFixture(t) {
  const root = workspace(t);
  const body = 'import { test } from "node:test"; test("fixture", () => {});';
  write(root, "scripts/nested folder/example.test.mjs", body);
  for (const path of TYPESCRIPT_TESTS) write(root, path, body);
  return root;
}

function standaloneChild(command, args, options) {
  const env = { ...process.env };
  // A fresh test runner must not inherit this test file's worker context.
  delete env.NODE_TEST_CONTEXT;
  return spawnSync(command, ["--test-reporter=tap", ...args], {
    ...options, env, stdio: "pipe", encoding: "utf8",
  });
}

test("discovery includes nested filenames with spaces and excludes helper modules", (t) => {
  const root = workspace(t);
  write(root, "scripts/z.test.mjs", "");
  write(root, "scripts/nested folder/a.test.mjs", "");
  write(root, "scripts/nested folder/helper.mjs", "");
  assert.deepEqual(discoverScriptTests(root), [
    join(root, "scripts/nested folder/a.test.mjs"),
    join(root, "scripts/z.test.mjs"),
  ]);
});

test("an empty or missing suite fails before spawning", (t) => {
  const root = workspace(t);
  const unexpected = () => assert.fail("must not spawn an incomplete suite");
  assert.throws(() => runTests(root, unexpected), /No script tests/);
  rmSync(join(root, "scripts"), { recursive: true });
  assert.throws(() => runTests(root, unexpected), /ENOENT/);
});

test("a missing required TypeScript file fails before spawning", (t) => {
  const root = completeFixture(t);
  rmSync(join(root, TYPESCRIPT_TESTS[0]));
  assert.throws(
    () => runTests(root, () => assert.fail("must validate both suites first")),
    /ENOENT/,
  );
});

test("actual child processes execute both suites from paths containing spaces", (t) => {
  const root = completeFixture(t);
  const results = [];
  assert.equal(runTests(root, (command, args, options) => {
    assert.equal(options.shell, false);
    const result = standaloneChild(command, args, options);
    results.push(result);
    return result;
  }), 0);
  assert.equal(results.length, 2);
  assert.match(results[0].stdout, /# tests 1\b/);
  assert.match(results[1].stdout, /# tests 4\b/);
});

test("a failing script test returns nonzero and stops the second suite", (t) => {
  const root = completeFixture(t);
  write(root, "scripts/failure.test.mjs", 'import { test } from "node:test"; test("failure", () => { throw new Error("intentional"); });');
  let calls = 0;
  const code = runTests(root, (command, args, options) => {
    calls += 1;
    return standaloneChild(command, args, options);
  });
  assert.equal(code, 1);
  assert.equal(calls, 1);
});

test("a second-suite failure, cancellation, or launch error cannot become success", (t) => {
  const root = completeFixture(t);
  let calls = 0;
  assert.equal(runTests(root, () => ({ status: ++calls === 1 ? 0 : 3 })), 3);
  for (const result of [{ status: null, signal: "SIGTERM" }, { status: null }, { status: -1 }]) {
    assert.throws(() => runTests(root, () => result), /did not complete/);
  }
  assert.throws(() => runTests(root, () => ({ error: new Error("launch failed") })), /launch failed/);
});
