import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the React app runs on :5444 and forwards API calls to Django on :8888.
// For deployment, `npm run build` creates dist/, which Django serves on :8888.
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: { assetsDir: "assets" },
  server: {
    port: 5444,
    proxy: { "/api": "http://127.0.0.1:8888", "/admin": "http://127.0.0.1:8888" },
  },
});
