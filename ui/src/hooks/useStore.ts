import { useSyncExternalStore } from "react";
import type { ReadableStore } from "../lib/createStore";

/** Subscribes a component to a store exposed by the api layer. */
export function useStore<T>(store: ReadableStore<T>): T {
  return useSyncExternalStore(store.subscribe, store.getSnapshot);
}
