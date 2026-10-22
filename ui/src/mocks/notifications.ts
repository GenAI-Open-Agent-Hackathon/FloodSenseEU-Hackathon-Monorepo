import type { AppNotification } from "../types";
import { approvalRequests } from "./approvals";
import { alerts } from "./portfolio";

/** Initial notifications, derived from the sample alerts and pending approvals. */
export const initialNotifications: AppNotification[] = [
  ...alerts.slice(0, 2).map((alert): AppNotification => ({
    id: `n-${alert.id}`,
    kind: "alert",
    title: alert.title,
    detail: alert.region,
    createdAt: alert.issuedAt,
    read: false,
  })),
  ...approvalRequests.map((request): AppNotification => ({
    id: `n-${request.id}`,
    kind: "approval-needed",
    title: "Approval needed",
    detail: request.title,
    createdAt: request.createdAt,
    read: request.id !== "ap-1",
    approvalId: request.id,
  })),
].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt));
