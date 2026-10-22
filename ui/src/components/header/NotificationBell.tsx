import { useCallback, useRef, useState } from "react";
import { markNotificationsRead, notifications } from "../../api/client";
import { useDismiss } from "../../hooks/useDismiss";
import { useStore } from "../../hooks/useStore";
import { formatTime } from "../../lib/format";
import type { NotificationKind } from "../../types";

const kindLabel: Record<NotificationKind, string> = {
  alert: "Alert",
  "approval-needed": "Approval needed",
  decision: "Decision",
};

export function NotificationBell() {
  const items = useStore(notifications);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(ref, open, close);
  const unread = items.filter((n) => !n.read).length;

  return (
    <div className="dropdown" ref={ref}>
      <button
        type="button"
        className="header-icon"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={`Notifications, ${unread} unread`}
        title="Notifications"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path d="M12 3a6 6 0 0 0-6 6v3.5L4.5 16h15L18 12.5V9a6 6 0 0 0-6-6zM9.5 18a2.5 2.5 0 0 0 5 0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
        </svg>
        {unread > 0 && <span className="header-icon__count">{unread}</span>}
      </button>
      {open && (
        <div className="dropdown__panel dropdown__panel--wide" role="dialog" aria-label="Notifications">
          <div className="dropdown__head">
            <strong>Notifications</strong>
            <button type="button" className="link-button small" onClick={() => void markNotificationsRead()} disabled={unread === 0}>
              Mark all read
            </button>
          </div>
          {items.length === 0 ? (
            <p className="muted small">No notifications.</p>
          ) : (
            <ul className="notification-list">
              {items.map((n) => (
                <li key={n.id} className={`notification notification--${n.kind} ${n.read ? "" : "is-unread"}`}>
                  <button type="button" className="notification__button" onClick={() => void markNotificationsRead([n.id])}>
                    <span className="notification__kind">{kindLabel[n.kind]}</span>
                    <span className="notification__title">{n.title}</span>
                    <span className="notification__detail">{n.detail}</span>
                    <span className="notification__time">{formatTime(n.createdAt)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="dropdown__foot muted small">Sample notifications. Nothing is emailed or pushed.</p>
        </div>
      )}
    </div>
  );
}
