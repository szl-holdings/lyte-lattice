import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { join } from "node:path";
import { test } from "node:test";
import { promisify } from "node:util";
import { mergeAppEnv, parseAppEnv, readAppEnv } from "./with-app-env.mjs";
import { aliasScripts, appEnvProcessEnv, makeAppEnvWorkspace } from "./test-support/app-env-fixture.mjs";

const execFileAsync = promisify(execFile);
const PRINT_FLAG = "process.stdout.write(String(process.env.VITE_AUTH_ENABLED));";

test("keeps VITE_-prefixed string entries", () => {
  assert.deepEqual(parseAppEnv('{"VITE_AUTH_ENABLED":"false"}'), {
    VITE_AUTH_ENABLED: "false",
  });
});

test("drops non-VITE keys, non-string values and malformed documents", () => {
  assert.deepEqual(parseAppEnv('{"DATABASE_URL":"postgres://x","VITE_N":1,"VITE_OK":"y"}'), {
    VITE_OK: "y",
  });
  assert.deepEqual(parseAppEnv("not json"), {});
  assert.deepEqual(parseAppEnv('["VITE_AUTH_ENABLED"]'), {});
  assert.deepEqual(parseAppEnv("null"), {});
});

test("a missing app-env.json is a clean no-op", (t) => {
  assert.deepEqual(readAppEnv(makeAppEnvWorkspace(t)), {});
});

test("reads the app env from a workspace", (t) => {
  const root = makeAppEnvWorkspace(t, '{"VITE_AUTH_ENABLED":"false"}');
  assert.deepEqual(readAppEnv(root), { VITE_AUTH_ENABLED: "false" });
});

test("an explicit process-env override wins over the file", () => {
  const merged = mergeAppEnv(
    { VITE_AUTH_ENABLED: "false" },
    { VITE_AUTH_ENABLED: "true", PATH: "/usr/bin" },
  );
  assert.equal(merged.VITE_AUTH_ENABLED, "true");
  assert.equal(merged.PATH, "/usr/bin");
});

test("a malformed app-env.json is a clean no-op", (t) => {
  assert.deepEqual(readAppEnv(makeAppEnvWorkspace(t, "not json")), {});
});

test("vite loadEnv resolves the wrapped value", (t) => {
  // What `import.meta.env.VITE_AUTH_ENABLED` becomes: loadEnv prefix-matches
  // process.env, so the wrapper's merge has to land before Vite starts.
  // Do not `import { loadEnv } from "vite"` here — Vite 8 loads rolldown
  // native bindings that SIGSEGV the test worker under qemu-user.
  const root = makeAppEnvWorkspace(t, '{"VITE_AUTH_ENABLED":"false"}');
  const merged = mergeAppEnv(readAppEnv(root), { PATH: "/usr/bin" });
  assert.equal(merged.VITE_AUTH_ENABLED, "false");
});

test("the wrapped command runs with the app env applied", async (t) => {
  const root = makeAppEnvWorkspace(t, '{"VITE_AUTH_ENABLED":"false"}');
  const { stdout } = await execFileAsync(process.execPath, [
    join(root, "scripts/with-app-env.mjs"),
    process.execPath,
    "-e",
    PRINT_FLAG,
  ], { env: appEnvProcessEnv() });
  assert.equal(stdout, "false");
});

test("the wrapped command sees an explicit override, not the file value", async (t) => {
  const root = makeAppEnvWorkspace(t, '{"VITE_AUTH_ENABLED":"false"}');
  const { stdout } = await execFileAsync(
    process.execPath,
    [join(root, "scripts/with-app-env.mjs"), process.execPath, "-e", PRINT_FLAG],
    { env: appEnvProcessEnv({ VITE_AUTH_ENABLED: "true" }) },
  );
  assert.equal(stdout, "true");
});

test("the wrapped command preserves an explicit false override of a true file", async (t) => {
  const root = makeAppEnvWorkspace(t, '{"VITE_AUTH_ENABLED":"true"}');
  const { stdout } = await execFileAsync(
    process.execPath,
    [join(root, "scripts/with-app-env.mjs"), process.execPath, "-e", PRINT_FLAG],
    { env: appEnvProcessEnv({ VITE_AUTH_ENABLED: "false" }) },
  );
  assert.equal(stdout, "false");
});

for (const [label, document] of [["absent", undefined], ["malformed", "not json"]]) {
  test(`the wrapped command keeps auth on when app-env.json is ${label}`, async (t) => {
    const root = makeAppEnvWorkspace(t, document);
    const { stdout } = await execFileAsync(process.execPath, [
      join(root, "scripts/with-app-env.mjs"),
      process.execPath,
      "--input-type=module",
      "-e",
      'import { authEnabledFromEnvValue } from "./scripts/check-auth-invariant.mjs"; ' +
        "process.stdout.write(JSON.stringify({ present: Object.hasOwn(process.env, 'VITE_AUTH_ENABLED'), " +
        "authEnabled: authEnabledFromEnvValue(process.env.VITE_AUTH_ENABLED) }));",
    ], { cwd: root, env: appEnvProcessEnv() });
    assert.deepEqual(JSON.parse(stdout), { present: false, authEnabled: true });
  });
}

test("the wrapper propagates the command's exit code", async (t) => {
  const root = makeAppEnvWorkspace(t);
  await assert.rejects(
    execFileAsync(process.execPath, [join(root, "scripts/with-app-env.mjs"), process.execPath, "-e", "process.exit(3)"]),
    (err) => err.code === 3,
  );
});

test("a signal-killed command is never reported as success", async (t) => {
  // The wrapper must propagate cancellation as a signal or nonzero exit status;
  // a cancelled build reporting exit 0 is a silently passing gate.
  const root = makeAppEnvWorkspace(t);
  await assert.rejects(
    execFileAsync(process.execPath, [
      join(root, "scripts/with-app-env.mjs"),
      process.execPath,
      "-e",
      "process.kill(process.pid, 'SIGTERM');setTimeout(() => {}, 1000);",
    ]),
    (err) => err.signal === "SIGTERM" || (Number.isInteger(err.code) && err.code > 0),
  );
});

test("the CLI still runs when invoked through a directory alias", async (t) => {
  // node realpaths import.meta.url but not process.argv[1], so a raw comparison
  // turns the wrapper into a no-op that exits 0 without starting anything.
  const root = makeAppEnvWorkspace(t, '{"VITE_AUTH_ENABLED":"false"}');
  const link = aliasScripts(root);
  const { stdout } = await execFileAsync(process.execPath, [
    join(link, "with-app-env.mjs"),
    process.execPath,
    "-e",
    PRINT_FLAG,
  ], { env: appEnvProcessEnv() });
  assert.equal(stdout, "false");
});
