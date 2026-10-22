/**
 * Current user. The mock has NO authentication: it returns fictional demo
 * users. Swap path: GET /me after the real sign-in flow; never handle
 * passwords in this UI.
 */
import { demoUsers } from "../mocks/users";
import type { DemoUser, UserRole } from "../types";
import { respond } from "./mockTransport";

export function getCurrentUser(role: UserRole): Promise<DemoUser> {
  return respond(demoUsers[role], 50);
}
