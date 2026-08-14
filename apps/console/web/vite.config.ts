import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const evidenceApi = "http://127.0.0.1:8000";
const managementApi = "http://127.0.0.1:8001";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      "/api/v2": managementApi,
      "/gateway": managementApi,
      "/api": evidenceApi,
      "/evidence": evidenceApi,
      "/health": evidenceApi,
      "/ready": evidenceApi,
      "/version": evidenceApi,
    },
  },
});
