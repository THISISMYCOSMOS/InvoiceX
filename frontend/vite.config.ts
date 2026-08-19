import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget =
    process.env.VITE_DEV_API_PROXY_TARGET ?? env.VITE_DEV_API_PROXY_TARGET;

  return {
    plugins: [react(), tailwindcss()],
    server: proxyTarget
    ? {
        proxy: {
          "/api": {
            target: proxyTarget,
            changeOrigin: true,
            secure: true,
            configure: (proxy) => {
              proxy.on("proxyReq", (request) => request.removeHeader("origin"));
            },
          },
        },
      }
    : undefined,
    test: {
      environment: "jsdom",
      environmentOptions: {
        jsdom: { url: "http://localhost/" },
      },
      setupFiles: "./src/test/setup.ts",
      globals: true,
    },
  };
});
