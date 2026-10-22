export type UserRole = "citizen" | "insurer";

/** The signed-in user. The mock has no authentication; these are fictional demo users. */
export interface DemoUser {
  id: string;
  displayName: string;
  initials: string;
  role: UserRole;
  organisation: string;
  email: string;
}
