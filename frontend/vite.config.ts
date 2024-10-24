import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import path from "path"

// https://vitejs.dev/config/
export default defineConfig((state) => ({
  plugins: [
    TanStackRouterVite(),
    react()
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
      outDir: "dist",
  },
  // TODO: figure out static files. may not even be needed since we can import assets from frontend/assets
  publicDir: false as const,
  // NOTE: this proxy is only used in dev mode
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    }
  }
}))
