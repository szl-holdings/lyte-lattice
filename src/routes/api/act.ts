import { createFileRoute } from "@tanstack/react-router";
import { spawn } from "node:child_process";
import path from "node:path";

const MAX_PAYLOAD = 64_000;
const TIMEOUT_MS = 12_000;

function runOrgan(cell: string, payload: unknown): Promise<{ stdout: string; stderr: string; code: number }> {
  const pythonRoot = path.join(process.cwd(), "python");
  const body = JSON.stringify(payload ?? {});
  return new Promise((resolve, reject) => {
    const child = spawn(
      "python3",
      ["-m", "lyte_lattice", "act", "--cell", cell, "--payload", body],
      {
        cwd: pythonRoot,
        env: { ...process.env, PYTHONPATH: pythonRoot, PYTHONDONTWRITEBYTECODE: "1" },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error("organ timed out"));
    }, TIMEOUT_MS);
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      stdout += chunk;
      if (stdout.length > 400_000) child.kill("SIGKILL");
    });
    child.stderr.on("data", (chunk: string) => {
      stderr += chunk;
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ stdout, stderr, code: code ?? 1 });
    });
  });
}

export const Route = createFileRoute("/api/act")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        let data: unknown;
        try {
          data = await request.json();
        } catch {
          return Response.json({ ok: false, error: "Invalid JSON" }, { status: 400 });
        }
        if (data === null || typeof data !== "object" || Array.isArray(data)) {
          return Response.json({ ok: false, error: "request must be a JSON object" }, { status: 400 });
        }
        const input = data as { cell?: unknown; payload?: unknown };
        const cell = typeof input.cell === "string" ? input.cell.trim() : "";
        if (!cell) {
          return Response.json({ ok: false, error: "cell required" }, { status: 400 });
        }
        const payload = input.payload ?? {};
        if (typeof payload !== "object" || Array.isArray(payload)) {
          return Response.json({ ok: false, error: "payload must be a JSON object" }, { status: 400 });
        }
        const raw = JSON.stringify(payload);
        // spawn transports the JSON argument as UTF-8, not UTF-16 code units.
        if (Buffer.byteLength(raw, "utf8") > MAX_PAYLOAD) {
          return Response.json({ ok: false, error: "payload too large" }, { status: 413 });
        }
        try {
          const { stdout, stderr, code } = await runOrgan(cell, payload);
          const line = stdout.trim().split("\n").filter(Boolean).pop() ?? "";
          if (!line) {
            return Response.json(
              { ok: false, error: stderr.slice(0, 400) || `organ exited ${code} with empty stdout` },
              { status: 502 },
            );
          }
          let receipt: unknown;
          try {
            receipt = JSON.parse(line);
          } catch {
            return Response.json({ ok: false, error: "organ returned non-JSON" }, { status: 502 });
          }
          return Response.json(receipt);
        } catch (err) {
          const message = err instanceof Error ? err.message : "organ failed";
          return Response.json({ ok: false, error: message }, { status: 500 });
        }
      },
    },
  },
});
