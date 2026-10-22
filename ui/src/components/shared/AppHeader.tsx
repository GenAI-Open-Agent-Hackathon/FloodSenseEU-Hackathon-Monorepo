import type { Route } from "../../hooks/useHashRoute";
import { MockBadge } from "./MockBadge";
import { RateLimitIndicator } from "./RateLimitIndicator";
import { NotificationBell } from "../header/NotificationBell";
import { ProfileMenu } from "../header/ProfileMenu";
import { ThemeToggle } from "../header/ThemeToggle";

interface AppHeaderProps {
  route: Route;
  onNavigate: (route: Route) => void;
}

const tabs: { route: Route; label: string; hint: string }[] = [
  { route: "citizen", label: "Citizen", hint: "Is my area at risk, and why?" },
  { route: "insurer", label: "Insurer", hint: "Portfolio exposure and approvals" },
];

export function AppHeader({ route, onNavigate }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
          <path d="M16 3c5 7 9 11.5 9 16.5a9 9 0 0 1-18 0C7 14.5 11 10 16 3z" fill="currentColor" />
          <path d="M10 21c2 1.5 4 1.5 6 0s4-1.5 6 0" className="app-header__logo-wave" strokeWidth="1.8" fill="none" strokeLinecap="round" />
        </svg>
        <div>
          <strong>FloodSense EU</strong>
          <span className="app-header__tagline">Cited flood-risk explanations</span>
        </div>
        <MockBadge label="MOCK UI" title="Mock interface. Figures are sample unless a Live badge says otherwise." />
      </div>
      <nav className="role-switch" aria-label="Choose a view">
        {tabs.map((tab) => (
          <button
            key={tab.route}
            type="button"
            className={`role-switch__tab ${route === tab.route ? "is-active" : ""}`}
            aria-current={route === tab.route ? "page" : undefined}
            onClick={() => onNavigate(tab.route)}
            title={tab.hint}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <div className="app-header__tools">
        <RateLimitIndicator />
        <ThemeToggle />
        {route === "insurer" && <NotificationBell />}
        <ProfileMenu role={route} />
      </div>
    </header>
  );
}
