import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5500,
    proxy: {
      "/patients": "http://127.0.0.1:9999",
      "/agreements": "http://127.0.0.1:9999",
      "/enrollments": "http://127.0.0.1:9999",
      "/medications": "http://127.0.0.1:9999",
      "/monodrugs": "http://127.0.0.1:9999",
    },
  },
});
