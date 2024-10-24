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
      outDir: "dist/vite",
  },
  base: state.mode === 'build' ? 'vite' : '/',
  publicDir: 'static',
  // NOTE: this only applies to dev mode
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    }
  }
}))
