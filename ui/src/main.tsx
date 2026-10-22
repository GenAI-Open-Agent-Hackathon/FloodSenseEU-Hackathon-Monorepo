import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { hideSplashAfterTimeout, setSplashStatus } from "./lib/splash";
import "./styles/global.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("root element missing");
}

setSplashStatus("Initialising the map…");
hideSplashAfterTimeout();

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
