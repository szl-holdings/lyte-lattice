import { createFileRoute } from "@tanstack/react-router";
import { handleComplete } from "@/lib/grok-stream.server";

export const Route = createFileRoute("/api/complete")({
  server: { handlers: { POST: ({ request }) => handleComplete(request) } },
});
