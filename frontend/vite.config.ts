import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import path from "path"

// https://vitejs.dev/config/
export default defineConfig(() => ({
  plugins: [
    TanStackRouterVite(),
    react()
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  base: '/static',
  build: {
      outDir: "dist/vite",
      manifest: 'manifest.json',
  },
  // TODO: figure out static files. may not even be needed since we can import assets from frontend/assets
  publicDir: false as const,
  server: {
    // origin: 'http://127.0.0.1:5173',
  }
}))
