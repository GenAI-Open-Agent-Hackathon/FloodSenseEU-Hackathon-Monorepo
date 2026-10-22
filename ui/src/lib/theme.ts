export type Theme = "light" | "dark";

/** Keep in sync with the inline script in index.html. */
const STORAGE_KEY = "floodsense.theme";

/** The theme applied by index.html before first paint. */
export function currentTheme(): Theme {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

/** Applies a theme and remembers it as an explicit user choice. */
export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Storage can be unavailable (private mode); the theme still applies for this visit.
  }
}

/** True when the user has not chosen a theme, so the OS preference applies. */
export function followsSystem(): boolean {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored !== "light" && stored !== "dark";
  } catch {
    return true;
  }
}
