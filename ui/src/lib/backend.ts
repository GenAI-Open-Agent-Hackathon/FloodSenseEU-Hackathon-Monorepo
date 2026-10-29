/**
 * Which data backend answered: "zetaris" (default) or "local" (Postgres, DATA_BACKEND=local).
 * Set once at boot from GET /config (data_backend). Every UI string that names the data
 * source goes through dataBackendName(), so a local run never says "Zetaris".
 */
let backend: "zetaris" | "local" = "zetaris";

export function setDataBackend(value: unknown): void {
  backend = value === "local" ? "local" : "zetaris";
}

export function dataBackendName(): string {
  return backend === "local" ? "Local Postgres" : "Zetaris";
}
