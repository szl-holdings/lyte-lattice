import { createFileRoute, redirect } from "@tanstack/react-router";
import { CoverView } from "@/components/cells/cover-view";
import { GraphView } from "@/components/cells/graph-view";
import { GuardView } from "@/components/cells/guard-view";
import { LatticeView } from "@/components/cells/lattice-view";
import { MosaicView } from "@/components/cells/mosaic-view";
import { ObserveView } from "@/components/cells/observe-view";
import { OrganDesk } from "@/components/cells/organ-desk";
import { QuantView } from "@/components/cells/quant-view";
import { RetrieveView } from "@/components/cells/retrieve-view";
import { SchemaView } from "@/components/cells/schema-view";
import { ServeView } from "@/components/cells/serve-view";
import { TuneView } from "@/components/cells/tune-view";
import { isCellId, type CellId } from "@/lib/cells";

export const Route = createFileRoute("/$cell")({
  beforeLoad: ({ params }) => {
    if (!isCellId(params.cell) || params.cell === "lyte") throw redirect({ to: "/" });
  },
  component: CellRoute,
});

function CellRoute() {
  const { cell } = Route.useParams();
  const id = cell as CellId;
  switch (id) {
    case "serve":
      return <ServeView />;
    case "graph":
      return <GraphView />;
    case "guard":
      return <GuardView />;
    case "mosaic":
      return <MosaicView />;
    case "lattice":
      return <LatticeView />;
    case "cover":
      return <CoverView />;
    case "quant":
      return <QuantView />;
    case "retrieve":
      return <RetrieveView />;
    case "observe":
      return <ObserveView />;
    case "tune":
      return <TuneView />;
    case "schema":
      return <SchemaView />;
    default:
      return <OrganDesk id={id} />;
  }
}
