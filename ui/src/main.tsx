import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/global.css";
import "./styles/agents.css";
import "./styles/clarity.css";
import { prefetchLiveWatch } from "./hooks/useLiveWatch";

const root = document.getElementById("root");
if (!root) {
  throw new Error("root element missing");
}

prefetchLiveWatch();

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
