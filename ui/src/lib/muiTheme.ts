import { createTheme } from "@mui/material/styles";

/** Status tones. Model output is never red: "elevated" is a strong amber, only measured "warning" uses the error hue. */
export type StatusTone = "normal" | "watch" | "elevated" | "warning" | "neutral" | "unknown";
export interface StatusColour {
  main: string;
  soft: string;
  ink: string;
  border: string;
}

declare module "@mui/material/styles" {
  interface Palette {
    status: Record<StatusTone, StatusColour>;
  }
  interface PaletteOptions {
    status?: Record<StatusTone, StatusColour>;
  }
}

const lightStatus: Record<StatusTone, StatusColour> = {
  normal: { main: "#2e8b57", soft: "#e5f4eb", ink: "#1f6b41", border: "#bfe3cd" },
  watch: { main: "#d19a00", soft: "#fdf3d6", ink: "#7a4b00", border: "#f0cf6b" },
  elevated: { main: "#e0662b", soft: "#fdf3d6", ink: "#7a4b00", border: "#7a4b00" },
  warning: { main: "#c62839", soft: "#fbe3e6", ink: "#b0202f", border: "#efb7be" },
  neutral: { main: "#0b5cad", soft: "#e6f0fb", ink: "#083f78", border: "#c8dcf3" },
  unknown: { main: "#8a97a8", soft: "#eef1f5", ink: "#46566b", border: "#e1e7ef" },
};
const darkStatus: Record<StatusTone, StatusColour> = {
  normal: { main: "#3fae6f", soft: "#173528", ink: "#8ddcae", border: "#2d6b48" },
  watch: { main: "#e0ad1f", soft: "#3a3014", ink: "#f3cf6e", border: "#8a7228" },
  elevated: { main: "#f07a3f", soft: "#3a3014", ink: "#f3cf6e", border: "#f3cf6e" },
  warning: { main: "#ec4d5c", soft: "#3e1c22", ink: "#ff9aa5", border: "#7a3640" },
  neutral: { main: "#4c9be8", soft: "#1b3350", ink: "#a9d0f7", border: "#2d5580" },
  unknown: { main: "#7b8899", soft: "#243245", ink: "#b9c7d8", border: "#2b3a50" },
};

const font = 'Inter, "Segoe UI", system-ui, -apple-system, Roboto, sans-serif';

// Follows the existing data-theme attribute set by lib/theme.ts, so no React state is needed.
export const muiTheme = createTheme({
  cssVariables: { colorSchemeSelector: '[data-theme="%s"]' },
  colorSchemes: {
    light: {
      palette: {
        primary: { main: "#0b5cad", dark: "#083f78", light: "#e6f0fb", contrastText: "#ffffff" },
        secondary: { main: "#5a3aa8" },
        success: { main: "#1f6b41" },
        warning: { main: "#7a4b00" },
        error: { main: "#b0202f" },
        info: { main: "#0b5cad" },
        background: { default: "#f3f6fa", paper: "#ffffff" },
        text: { primary: "#13233a", secondary: "#5b6b80" },
        divider: "#e1e7ef",
        status: lightStatus,
      },
    },
    dark: {
      palette: {
        primary: { main: "#4c9be8", dark: "#a9d0f7", light: "#1b3350", contrastText: "#0b1626" },
        secondary: { main: "#c4b5ff" },
        success: { main: "#8ddcae" },
        warning: { main: "#f3cf6e" },
        error: { main: "#ff9aa5" },
        info: { main: "#4c9be8" },
        background: { default: "#0e1622", paper: "#162131" },
        text: { primary: "#e6edf6", secondary: "#9aabc0" },
        divider: "#2b3a50",
        status: darkStatus,
      },
    },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: font,
    fontSize: 15,
    h1: { fontSize: "1.75rem", fontWeight: 700, lineHeight: 1.2 },
    h2: { fontSize: "1.5rem", fontWeight: 700, lineHeight: 1.25 },
    h3: { fontSize: "1.2rem", fontWeight: 650, lineHeight: 1.3 },
    h4: { fontSize: "1.05rem", fontWeight: 650, lineHeight: 1.35 },
    subtitle1: { fontSize: "1rem", fontWeight: 600 },
    subtitle2: { fontSize: "0.875rem", fontWeight: 600 },
    body1: { fontSize: "0.9375rem", lineHeight: 1.55 },
    body2: { fontSize: "0.85rem", lineHeight: 1.5 },
    caption: { fontSize: "0.78rem" },
    overline: { fontSize: "0.72rem", fontWeight: 650, letterSpacing: "0.08em" },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiCard: { defaultProps: { variant: "outlined" }, styleOverrides: { root: { borderRadius: 12 } } },
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { borderRadius: 8, minHeight: 36 } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 600, borderRadius: 999 } } },
    MuiTableCell: {
      styleOverrides: {
        head: ({ theme }) => ({ fontWeight: 650, color: theme.vars.palette.text.secondary, backgroundColor: theme.vars.palette.background.paper }),
      },
    },
    MuiTabs: { styleOverrides: { indicator: { height: 3, borderRadius: 3 } } },
    MuiTab: { styleOverrides: { root: { minHeight: 44, fontWeight: 600 } } },
    MuiDrawer: { styleOverrides: { paper: { backgroundImage: "none" } } },
  },
});
