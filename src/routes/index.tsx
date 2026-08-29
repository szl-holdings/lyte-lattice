import { createFileRoute } from "@tanstack/react-router";
import { LyteView } from "@/components/cells/lyte-view";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  return <LyteView />;
}
