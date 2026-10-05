import { copyFileSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Exercise the real CLI modules without depending on an ignored developer file
// or creating an auth override in the repository being tested.
export function makeAppEnvWorkspace(t, appEnvJson) {
  const root = mkdtempSync(join(tmpdir(), "lyte-app-env-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  mkdirSync(join(root, "scripts"));
  for (const name of ["with-app-env.mjs", "check-auth-invariant.mjs", "app-env-plugin.mjs"]) {
    copyFileSync(new URL(`../${name}`, import.meta.url), join(root, "scripts", name));
  }
  if (appEnvJson !== undefined) {
    mkdirSync(join(root, ".grok"));
    writeFileSync(join(root, ".grok/app-env.json"), appEnvJson);
  }
  return root;
}

export function appEnvProcessEnv(overrides = {}) {
  const env = { ...process.env };
  // Environment keys are case-insensitive on Windows.
  for (const key of Object.keys(env)) {
    if (key.toUpperCase() === "VITE_AUTH_ENABLED") delete env[key];
  }
  return { ...env, ...overrides };
}

export function aliasScripts(root) {
  const link = join(root, "scripts-alias");
  symlinkSync(join(root, "scripts"), link, process.platform === "win32" ? "junction" : "dir");
  return link;
}
