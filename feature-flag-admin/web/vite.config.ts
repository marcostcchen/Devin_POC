import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The FastAPI app serves dist/ directly, so `vite build` writes there and the
// dev server (`npm run dev`) proxies the API to uvicorn on :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
