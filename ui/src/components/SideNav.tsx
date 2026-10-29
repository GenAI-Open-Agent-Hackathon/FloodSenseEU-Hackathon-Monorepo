import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { DESK_NAV, routeHref } from "../lib/route";
import { useConsole } from "../context/ConsoleContext";

/** Desktop widths mirror --nav-width in global.css (10.5rem open, 3.5rem collapsed). */
const OPEN_WIDTH = "10.5rem";
const COLLAPSED_WIDTH = "3.5rem";

/**
 * Pages of the current desk. Wide screens: a permanent MUI Drawer that collapses to an icon rail.
 * Phones (`drawer`): a temporary Drawer; MUI traps Tab inside, closes on Escape or backdrop click and returns focus to the toggle.
 */
export function SideNav({
  collapsed,
  onToggle,
  onNavigate,
  drawer = false,
}: {
  collapsed: boolean;
  onToggle: () => void;
  onNavigate: () => void;
  /** Phone drawer. */
  drawer?: boolean;
}) {
  const { route, page } = useConsole();
  const desk = route === "citizen" ? "Citizen" : route === "operator" ? "Civil protection" : "Insurer";
  const items = DESK_NAV[route];
  const toggle = (
    <IconButton
      type="button"
      aria-expanded={!collapsed}
      aria-controls="desk-pages"
      onClick={onToggle}
      sx={drawer ? { position: "fixed", top: 8, left: 8, zIndex: (t) => t.zIndex.appBar + 1 } : undefined}
    >
      <span className="sr-only">{collapsed ? "Show pages" : "Hide pages"}</span>
      <NavIcon />
    </IconButton>
  );
  const links = (
    <Box id="desk-pages" hidden={collapsed && !drawer}>
      <Typography variant="overline" color="text.secondary" component="p" sx={{ m: 0, px: 1 }}>
        {desk}
      </Typography>
      <List component="ul" dense disablePadding>
        {items.map((item) => (
          <li key={item.page}>
            <ListItemButton component="a" href={routeHref(route, item.page)} selected={page === item.page} aria-current={page === item.page ? "page" : undefined} onClick={onNavigate} sx={{ borderRadius: 2 }}>
              <ListItemText primary={item.label} slotProps={{ primary: { sx: { fontWeight: page === item.page ? 650 : 400 } } }} />
            </ListItemButton>
          </li>
        ))}
      </List>
    </Box>
  );

  if (drawer)
    return (
      <>
        {toggle}
        <Drawer variant="temporary" open={!collapsed} onClose={onToggle} ModalProps={{ keepMounted: false }} slotProps={{ paper: { sx: { width: "min(16rem, 80vw)", p: 1.5 } } }}>
          <nav aria-label={`${desk} pages`}>{links}</nav>
        </Drawer>
      </>
    );

  const width = collapsed ? COLLAPSED_WIDTH : OPEN_WIDTH;
  return (
    <Drawer variant="permanent" sx={{ width, flexShrink: 0 }} slotProps={{ paper: { sx: { width, p: 1, gap: 1, alignItems: collapsed ? "center" : "stretch", boxSizing: "border-box" } } }}>
      <nav aria-label={`${desk} pages`}>
        {toggle}
        {links}
      </nav>
    </Drawer>
  );
}

function NavIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M4 7h16M4 12h16M4 17h16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
