import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev server listens on 5173 both locally (http://localhost:5173) and inside
// the compose container, where it is published on host port 15173.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
  },
});
