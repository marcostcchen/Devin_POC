import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // The POC platform mounts this app at /apps/refunds-dashboard, so the build
  // must emit asset and API URLs under that prefix. `base` flows into
  // `import.meta.env.BASE_URL`, which apiClient.js prepends to every request.
  const platformBasePath = (
    process.env.PLATFORM_BASE_PATH ??
    env.PLATFORM_BASE_PATH ??
    ""
  ).replace(/\/$/, "");

  return {
    base: platformBasePath ? `${platformBasePath}/` : "/",
    define: {
      "import.meta.env.VITE_PLATFORM_BASE_PATH":
        JSON.stringify(platformBasePath),
    },
    plugins: [react()],
    server: {
      port: Number(env.VITE_PORT ?? 5173),
      strictPort: true,
    },
  };
});
