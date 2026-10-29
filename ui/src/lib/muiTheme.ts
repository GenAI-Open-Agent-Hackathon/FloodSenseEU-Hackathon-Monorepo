import { createTheme } from "@mui/material/styles";

// Follows the existing data-theme attribute set by lib/theme.ts, so no React state is needed.
export const muiTheme = createTheme({
  cssVariables: { colorSchemeSelector: '[data-theme="%s"]' },
  colorSchemes: {
    light: { palette: { primary: { main: "#0b6e6e" }, background: { default: "#f6f8f9", paper: "#ffffff" } } },
    dark: { palette: { primary: { main: "#4fd1c5" }, background: { default: "#0f1719", paper: "#162124" } } },
  },
  shape: { borderRadius: 10 },
  typography: { fontFamily: 'Inter, system-ui, "Segoe UI", sans-serif', button: { textTransform: "none", fontWeight: 600 } },
});
