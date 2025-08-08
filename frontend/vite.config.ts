import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
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
    sourcemap: true, // Generate source maps for development
    minify: false, // Don't minify for easier debugging
  },
  define: {
    __DEV__: true, // Define development flag
  },
})
