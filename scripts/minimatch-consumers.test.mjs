import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { ESLint } from "eslint";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const consumers = ["eslint", "@eslint/config-array", "@typescript-eslint/typescript-estree"];
const parser = createRequire(join(root, "node_modules/typescript-eslint/package.json"))("@typescript-eslint/parser");

for (const consumer of consumers) {
  test(`${consumer} uses bounded minimatch preprocessing`, () => {
    const requireFromConsumer = createRequire(join(root, "node_modules", consumer, "package.json"));
    const modulePath = requireFromConsumer.resolve("minimatch");
    // Exercise the advisory's expansion with a small synthetic input, in a
    // subprocess capped in time and heap even if a future dependency regresses.
    const child = spawnSync(process.execPath, ["--max-old-space-size=128", "-e", `
      const { Minimatch } = require(process.argv[1]);
      const pattern = Array(8).fill('**/../a/b').join('/');
      const matcher = new Minimatch(pattern, { optimizationLevel: 2, braceExpandMax: 64 });
      process.stdout.write(JSON.stringify({ patterns: matcher.set.length,
        matches: matcher.match(Array(8).fill('../a/b').join('/')) }));
    `, modulePath], { encoding: "utf8", timeout: 5000, maxBuffer: 16384 });
    assert.ifError(child.error);
    assert.equal(child.signal, null);
    assert.equal(child.status, 0, child.stderr);
    const result = JSON.parse(child.stdout);
    assert.ok(result.patterns <= 64, `preprocessing expanded to ${result.patterns} patterns`);
    assert.equal(result.matches, true);
  });
}

function fixture(files) {
  const directory = mkdtempSync(join(tmpdir(), "lyte-minimatch-"));
  for (const [path, contents] of Object.entries(files)) {
    const full = join(directory, path);
    mkdirSync(dirname(full), { recursive: true });
    writeFileSync(full, contents);
  }
  return directory;
}

test("ESLint retains actual config file selection, ignores, negation and partial paths", async () => {
  const source = "export const value = 1;\n";
  const cwd = fixture({
    "src/main.ts": source,
    "src/deep/widget.tsx": source,
    "src/.hidden.ts": source,
    "src/routeTree.gen.ts": source,
    "src/ignored/drop.ts": source,
    "src/ignored/keep.ts": source,
    "node_modules/example/index.ts": source,
    "dist/result.ts": source,
  });
  try {
    const eslint = new ESLint({
      cwd,
      overrideConfigFile: join(root, "eslint.config.mjs"),
      overrideConfig: [{ ignores: ["src/ignored/*.ts", "!src/ignored/keep.ts"] }],
    });
    const results = await eslint.lintFiles(["src/**/*.{ts,tsx}"]);
    assert.deepEqual(results.map((result) => relative(cwd, result.filePath).replaceAll("\\", "/")).sort(),
      ["src/.hidden.ts", "src/deep/widget.tsx", "src/ignored/keep.ts", "src/main.ts"]);
    assert.ok(results.every((result) => result.fatalErrorCount === 0));
    assert.equal(await eslint.isPathIgnored(join(cwd, "dist/result.ts")), true);
    assert.equal(await eslint.isPathIgnored(join(cwd, "node_modules/example/index.ts")), true);
    await assert.rejects(eslint.lintFiles(["missing/**/*.ts"]), /No files matching/);
  } finally {
    rmSync(cwd, { recursive: true, force: true });
  }
});

test("TypeScript project-service default-project globs admit only matching files", () => {
  const cwd = fixture({
    "tsconfig.json": JSON.stringify({ compilerOptions: { strict: true }, include: ["project/**/*.ts"] }),
    "project/included.ts": "export const included: number = 1;\n",
    "standalone.ts": "export const outside: number = 1;\n",
    "nested/denied.ts": "export const denied: number = 1;\n",
  });
  const options = {
    tsconfigRootDir: cwd,
    projectService: { allowDefaultProject: ["*.ts"], defaultProject: "tsconfig.json" },
  };
  try {
    const result = parser.parseForESLint("export const outside: number = 1;", {
      ...options, filePath: join(cwd, "standalone.ts"),
    });
    assert.ok(result.services.program);
    assert.throws(() => parser.parseForESLint("export const denied: number = 1;", {
      ...options, filePath: join(cwd, "nested/denied.ts"),
    }), /not found by the project service/);
  } finally {
    parser.clearCaches();
    rmSync(cwd, { recursive: true, force: true });
  }
});
