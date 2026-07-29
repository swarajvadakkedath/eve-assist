import { useSyncExternalStore } from "react";
import { getCommandStore } from "./CommandStore";

export function useCommandStore() {
  const store = getCommandStore();
  return useSyncExternalStore(
    (cb) => store.subscribe(cb),
    () => store.getState(),
    () => store.getState(),
  );
}
