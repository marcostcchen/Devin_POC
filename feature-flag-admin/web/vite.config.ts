import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The FastAPI app serves dist/ directly, so `vite build` writes there and the
// dev server (`npm run dev`) proxies the API to uvicorn on :8000.
//
// Under the POC platform the app is mounted at /apps/feature-flag-admin, so the
// build has to emit asset and API URLs under that prefix; `base` flows into
// `import.meta.env.BASE_URL`, which api.ts prepends to every request.
const basePath = process.env.PLATFORM_BASE_PATH
  ? `${process.env.PLATFORM_BASE_PATH.replace(/\/$/, "")}/`
  : "/";

export default defineConfig({
  base: basePath,
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
