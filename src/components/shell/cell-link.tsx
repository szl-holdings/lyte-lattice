import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import type { CellId } from "@/lib/cells";

export function CellLink({
  id,
  className,
  children,
}: {
  id: CellId;
  className?: string;
  children: ReactNode;
}) {
  if (id === "lyte") {
    return (
      <Link to="/" className={className}>
        {children}
      </Link>
    );
  }
  return (
    <Link to="/$cell" params={{ cell: id }} className={className}>
      {children}
    </Link>
  );
}
