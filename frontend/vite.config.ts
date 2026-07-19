import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In production the app is served under the gateway at /anonymizer, so assets must
// be referenced with that base. In dev Vite serves it at the root and proxies the
// API to the local backend on :8400.
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === "production" ? "/anonymizer/" : "/",
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8400",
    },
  },
}));
