/** Browser-facing API base. Vite inlines VITE_* into the bundle. Do not put secrets here. */
export function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_URL?.trim();
  const base = configured && configured.length > 0 ? configured : "http://localhost:18000";
  return base.replace(/\/+$/, "");
}
