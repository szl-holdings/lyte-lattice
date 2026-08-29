import { useEffect } from "react";
import { useLyte } from "@/lib/store";

export function HydrateStore() {
  useEffect(() => {
    void useLyte.persist.rehydrate();
    useLyte.getState().setHydrated();
  }, []);
  return null;
}
