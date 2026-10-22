/**
 * In-app notifications for the header bell.
 * Swap path: fill the store from GET /notifications and push new items from a
 * server-sent events stream; components keep reading the same store.
 */
import { initialNotifications } from "../mocks/notifications";
import { createStore, type ReadableStore } from "../lib/createStore";
import type { AppNotification } from "../types";

const store = createStore<AppNotification[]>(initialNotifications);

export const notifications: ReadableStore<AppNotification[]> = store;

/** Adds a notification at the top. Used by other api modules, not by components. */
export function pushNotification(notification: Omit<AppNotification, "id" | "createdAt" | "read">): void {
  const item: AppNotification = { ...notification, id: `n-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, createdAt: new Date().toISOString(), read: false };
  store.update((list) => [item, ...list]);
}

export function markNotificationsRead(ids?: readonly string[]): Promise<void> {
  store.update((list) => list.map((n) => (!ids || ids.includes(n.id) ? { ...n, read: true } : n)));
  return Promise.resolve();
}

/** Marks the "approval needed" notification for a request as read. */
export function resolveApprovalNotification(approvalId: string): void {
  store.update((list) => list.map((n) => (n.kind === "approval-needed" && n.approvalId === approvalId ? { ...n, read: true } : n)));
}
