import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { fetchAgentsConfig } from "./api/config";
import { setDataBackend } from "./lib/backend";
import "./styles/global.css";
import "./styles/agents.css";
import "./styles/clarity.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("root element missing");
}

// Name the data backend (Zetaris or local Postgres) before the first paint, but never
// hold the app for more than 1.5 s: if /config is slow the default label stays.
const backend = fetchAgentsConfig().then((r) => {
  if (r.kind === "ok") setDataBackend((r.body as { data_backend?: unknown } | null)?.data_backend);
});
const cap = new Promise((resolve) => setTimeout(resolve, 1500));

void Promise.race([backend, cap]).then(() => {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
