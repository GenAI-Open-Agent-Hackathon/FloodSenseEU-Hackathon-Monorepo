import { useEffect, useState } from "react";
import AppBar from "@mui/material/AppBar";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { useConsole } from "../context/ConsoleContext";
import { headerSubtitle } from "../lib/events";
import { ModeSwitch } from "./ModeSwitch";
import { useLiveWatch } from "../hooks/useLiveWatch";
import { plainOf, worstFirst } from "../lib/places";
import { applyTheme, readTheme, type ThemeName } from "../lib/theme";

const WORKSPACES = [
  { route: "citizen", label: "Citizen" },
  { route: "insurer", label: "Insurer" },
  { route: "operator", label: "Civil protection" },
] as const;

export function Header() {
  const desk = useConsole();
  const [theme, setTheme] = useState<ThemeName>(readTheme);
  const [bellEl, setBellEl] = useState<HTMLElement | null>(null);
  const [profileEl, setProfileEl] = useState<HTMLElement | null>(null);
  const live = useLiveWatch();
  // The bell's number is real: sources at their raised band right now (Live mode only), plus unread simulation notices.
  const raised = desk.mode === "live" ? live.sources.filter((s) => s.status === "over") : [];
  const watching = desk.mode === "live" ? live.sources.filter((s) => s.status === "near" || s.status === "over") : [];
  const unread = raised.length + desk.notices.filter((notice) => !notice.read).length;
  const markNotificationsRead = desk.markNotificationsRead;
  const bellOpen = Boolean(bellEl);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (bellOpen) markNotificationsRead();
  }, [bellOpen, markNotificationsRead]);

  const tab = WORKSPACES.some((w) => w.route === desk.route) ? desk.route : false;

  return (
    <AppBar component="header" position="sticky" color="default" elevation={0} sx={{ borderBottom: 1, borderColor: "divider", bgcolor: "background.paper" }}>
      <a className="skip" href="#content">
        Skip to content
      </a>
      <Toolbar sx={{ gap: 2, flexWrap: "wrap", "@media (max-width:760px)": { pl: 7 } }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, color: "primary.main" }}>
          <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true">
            <rect width="32" height="32" rx="8" fill="currentColor" opacity="0.16" />
            <path d="M5 20c3-4 5-4 8 0s5 4 8 0 5-4 6 0" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="M5 14c3-3 5-3 8 0s5 3 8 0 5-3 6 0" fill="none" stroke="currentColor" strokeWidth="2" />
          </svg>
          <Box sx={{ color: "text.primary" }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
              FloodSense EU
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {headerSubtitle()}
            </Typography>
          </Box>
        </Box>
        <Tabs value={tab} aria-label="Workspace" variant="scrollable" scrollButtons={false} sx={{ flex: 1, minWidth: 260 }}>
          {WORKSPACES.map((w) => (
            <Tab key={w.route} value={w.route} label={w.label} component="a" href={`#/${w.route}`} />
          ))}
        </Tabs>
        <IconButton
          aria-pressed={theme === "dark"}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          onClick={() => {
            const next = theme === "dark" ? "light" : "dark";
            setTheme(next);
            applyTheme(next);
          }}
        >
          {theme === "dark" ? <SunIcon /> : <MoonIcon />}
        </IconButton>
        <IconButton aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"} onClick={(e) => setBellEl(e.currentTarget)}>
          <Badge badgeContent={unread} color="error">
            <BellIcon />
          </Badge>
        </IconButton>
        <Popover open={bellOpen} anchorEl={bellEl} onClose={() => setBellEl(null)} anchorOrigin={{ vertical: "bottom", horizontal: "right" }} transformOrigin={{ vertical: "top", horizontal: "right" }}>
          <Box sx={{ p: 2, maxWidth: 360 }} role="dialog" aria-label="Notices">
            <Typography variant="overline" color="text.secondary">
              Notices
            </Typography>
            {desk.mode === "live" && live.sources.length > 0 && (
              <Box sx={{ mb: 1 }}>
                <Typography variant="subtitle2">Live watch</Typography>
                <Typography variant="body2">
                  {raised.length} of {live.sources.length} sources at their raised band; {watching.length - raised.length} slightly up.
                  {worstFirst(watching).slice(0, 3).length > 0 &&
                    ` Most notable: ${worstFirst(watching)
                      .slice(0, 3)
                      .map((s) => `${s.name} (${plainOf(s).word})`)
                      .join(", ")}.`}
                </Typography>
              </Box>
            )}
            {desk.notices.length === 0 ? (
              <Typography variant="body2">{desk.mode === "live" && live.sources.length > 0 ? "No other notices." : "No notices."}</Typography>
            ) : (
              desk.notices.map((notice) => (
                <Box key={notice.id} sx={{ mb: 1 }}>
                  <Typography variant="subtitle2">{notice.title}</Typography>
                  <Typography variant="body2">{notice.body}</Typography>
                </Box>
              ))
            )}
          </Box>
        </Popover>
        <IconButton aria-label="Account" onClick={(e) => setProfileEl(e.currentTarget)}>
          <PersonIcon />
        </IconButton>
        <Popover open={Boolean(profileEl)} anchorEl={profileEl} onClose={() => setProfileEl(null)} anchorOrigin={{ vertical: "bottom", horizontal: "right" }} transformOrigin={{ vertical: "top", horizontal: "right" }}>
          <Box sx={{ p: 2, maxWidth: 300 }} role="dialog" aria-label="Account">
            <Typography variant="body2" sx={{ mb: 1.5 }}>
              Sign-in is not wired on this build. No credentials are collected.
            </Typography>
            <Button variant="contained" disabled>
              Sign in
            </Button>
          </Box>
        </Popover>
      </Toolbar>
      <ModeSwitch />
    </AppBar>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <circle cx="12" cy="12" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M15 3.5a8 8 0 1 0 5.5 13.5A7 7 0 0 1 15 3.5z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M6 16h12l-1.2-2.2V10a4.8 4.8 0 0 0-9.6 0v3.8L6 16z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M10 16a2 2 0 0 0 4 0" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <circle cx="12" cy="9" r="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M5.5 19c1.4-2.4 3.6-3.5 6.5-3.5s5.1 1.1 6.5 3.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
