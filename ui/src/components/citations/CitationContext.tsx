import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { Citation } from "../../types";

export interface OpenCitation {
  citation: Citation;
  /** Display number of the marker that was clicked, e.g. 2 for [2]. */
  number: number;
}

interface CitationContextValue {
  active: OpenCitation | null;
  open: (citation: Citation, number: number) => void;
  close: () => void;
}

const CitationContext = createContext<CitationContextValue | null>(null);

/** Holds the single citation drawer state for the whole app. */
export function CitationProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<OpenCitation | null>(null);
  const open = useCallback((citation: Citation, number: number) => setActive({ citation, number }), []);
  const close = useCallback(() => setActive(null), []);
  const value = useMemo(() => ({ active, open, close }), [active, open, close]);
  return <CitationContext.Provider value={value}>{children}</CitationContext.Provider>;
}

export function useCitationPanel(): CitationContextValue {
  const context = useContext(CitationContext);
  if (!context) {
    throw new Error("useCitationPanel must be used inside <CitationProvider>");
  }
  return context;
}
