import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// MENTORIA_API_URL lets a second copy of the UI talk to an API on another port (default :8000).
// Read via globalThis so the config type-checks without Node typings.
const env: Record<string, string | undefined> =
  (globalThis as { process?: { env: Record<string, string | undefined> } }).process?.env ?? {};
const apiTarget = env.MENTORIA_API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(env.MENTORIA_WEB_PORT ?? 5173),
    proxy: { "/api": { target: apiTarget, changeOrigin: true } },
  },
});
