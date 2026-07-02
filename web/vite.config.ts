import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The web app talks to the FastAPI backend at /api/v1. In dev, proxy those calls
// to the local uvicorn server (override the target with VITE_API_TARGET).
const API_TARGET = process.env.VITE_API_TARGET ?? "http://127.0.0.1:8099";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Bind on both IPv4 and IPv6 so http://localhost, http://127.0.0.1, and
    // http://[::1] all resolve — a bare `localhost` that maps to IPv4 was
    // getting connection-refused when Vite listened on IPv6 only.
    host: true,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
    },
  },
});
