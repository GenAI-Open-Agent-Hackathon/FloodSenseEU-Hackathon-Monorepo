import type { DemoUser, UserRole } from "../types";

/** FICTIONAL demo users. The mock has no authentication. */
export const demoUsers: Record<UserRole, DemoUser> = {
  insurer: {
    id: "u-demo-underwriter",
    displayName: "Demo Underwriter",
    initials: "DU",
    role: "insurer",
    organisation: "Demo Insurance (fictional)",
    email: "underwriter@demo-insurer.example",
  },
  citizen: {
    id: "u-demo-resident",
    displayName: "Demo Resident",
    initials: "DR",
    role: "citizen",
    organisation: "Public user",
    email: "resident@example.org",
  },
};
