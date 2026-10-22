import { useEffect, useState } from "react";

export type AsyncState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: Error };

/** Runs an async loader whenever `deps` change and ignores stale results. */
export function useAsync<T>(load: () => Promise<T>, deps: readonly unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    load()
      .then((data) => active && setState({ status: "success", data }))
      .catch((error: unknown) => active && setState({ status: "error", error: error instanceof Error ? error : new Error(String(error)) }));
    return () => {
      active = false;
    };
    // The caller owns the dependency list, exactly like useEffect itself.
  }, deps);

  return state;
}
