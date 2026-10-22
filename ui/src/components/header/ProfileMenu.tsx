import { useCallback, useRef, useState } from "react";
import { getCurrentUser } from "../../api/client";
import { useAsync } from "../../hooks/useAsync";
import { useDismiss } from "../../hooks/useDismiss";
import type { UserRole } from "../../types";

/** Avatar menu for the fictional demo user. There is no authentication in the mock. */
export function ProfileMenu({ role }: { role: UserRole }) {
  const user = useAsync(() => getCurrentUser(role), [role]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(ref, open, close);

  if (user.status !== "success") {
    return <span className="avatar avatar--placeholder" aria-hidden="true" />;
  }
  const u = user.data;
  return (
    <div className="dropdown" ref={ref}>
      <button type="button" className={`avatar avatar--${u.role}`} onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="true" aria-label={`Account: ${u.displayName}`} title={u.displayName}>
        {u.initials}
      </button>
      {open && (
        <div className="dropdown__panel" role="dialog" aria-label="Account">
          <div className="profile">
            <span className={`avatar avatar--${u.role} avatar--lg`} aria-hidden="true">
              {u.initials}
            </span>
            <div>
              <strong>{u.displayName}</strong>
              <span className="muted small">{u.organisation}</span>
              <span className="muted small">{u.email}</span>
            </div>
          </div>
          <p className="notice small">Fictional demo user. The mock has no sign-in; real authentication comes with the backend.</p>
        </div>
      )}
    </div>
  );
}
