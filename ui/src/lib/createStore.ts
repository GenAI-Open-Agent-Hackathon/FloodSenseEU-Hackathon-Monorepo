/** Read-only view of an external store, for useSyncExternalStore. */
export interface ReadableStore<T> {
  getSnapshot: () => T;
  subscribe: (listener: () => void) => () => void;
}

export interface WritableStore<T> extends ReadableStore<T> {
  set: (next: T) => void;
  update: (change: (current: T) => T) => void;
}

/** Minimal observable value. Snapshots are replaced, never mutated. */
export function createStore<T>(initial: T): WritableStore<T> {
  let value = initial;
  const listeners = new Set<() => void>();
  const set = (next: T) => {
    value = next;
    listeners.forEach((listener) => listener());
  };
  return {
    getSnapshot: () => value,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    set,
    update: (change) => set(change(value)),
  };
}
