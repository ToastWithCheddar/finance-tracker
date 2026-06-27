import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  // Load .env files from the repo root so frontend uses unified env
  envDir: '..',
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow external connections
    port: 3000,
    strictPort: false, // Allow fallback ports for development
    open: true, // Auto-open browser
    watch: {
      usePolling: true, // Enable polling for file changes
    },
    hmr: {
      port: 3001, // Use different port for HMR
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: false,
  },
  build: {
    // Hidden sourcemaps: produced for upload to Sentry but not referenced from JS bundles in production.
    sourcemap: 'hidden',
    // Use esbuild for fast, production-grade minification.
    minify: 'esbuild',
  },
  define: {
    // Reflect actual build mode rather than hard-coding development.
    __DEV__: JSON.stringify(mode === 'development'),
  },
}))
