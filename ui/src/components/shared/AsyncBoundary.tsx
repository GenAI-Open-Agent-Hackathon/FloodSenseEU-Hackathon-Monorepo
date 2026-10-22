import type { ReactNode } from "react";
import type { AsyncState } from "../../hooks/useAsync";

interface AsyncBoundaryProps<T> {
  state: AsyncState<T>;
  children: (data: T) => ReactNode;
  loadingText?: string;
}

/** Renders loading and error states consistently for any useAsync result. */
export function AsyncBoundary<T>({ state, children, loadingText = "Loading…" }: AsyncBoundaryProps<T>) {
  if (state.status === "loading") {
    return <p className="muted loading">{loadingText}</p>;
  }
  if (state.status === "error") {
    return <p className="error" role="alert">{state.error.message}</p>;
  }
  return <>{children(state.data)}</>;
}
