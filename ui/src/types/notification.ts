export type NotificationKind = "alert" | "approval-needed" | "decision";

export interface AppNotification {
  id: string;
  kind: NotificationKind;
  title: string;
  detail: string;
  /** ISO 8601 timestamp. */
  createdAt: string;
  read: boolean;
  /** Approval request this notification refers to, if any. */
  approvalId?: string;
}
