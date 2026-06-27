import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_SRC = path.resolve(__dirname, 'src');

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': FRONTEND_SRC,
    },
    // Dedupe forces a single copy of these libraries, preventing the classic
    // "useContext returned null" provider mismatch when hooks tested via
    // @/hooks/... resolve into a different module graph than the test imports.
    dedupe: ['react', 'react-dom', '@tanstack/react-query', 'react-router-dom', 'zustand'],
  },
  // Mirror the frontend's Vite define so source files that read `__DEV__`
  // do not blow up when imported under Vitest.
  define: {
    __DEV__: true,
  },
  test: {
    globals: true,
    // jsdom is used because happy-dom@15 incorrectly locks the fetch
    // ReadableStream after a single Response.json()/text() read, which causes
    // src/services/api.ts to throw with `Invalid state: ReadableStream is
    // locked` on every request. jsdom's whatwg-fetch implementation handles
    // this correctly. See docs/integration/13b-frontend-fixture-pass.md.
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules/**', 'src/**'],
    css: false,
    // Surface unhandled rejections so MSW unhandled-request warnings are visible.
    dangerouslyIgnoreUnhandledErrors: false,
    // Each test file gets a fresh module registry — important since several
    // source modules construct singletons at import time (apiClient, secureStorage).
    isolate: true,
    env: {
      VITE_API_URL: 'http://localhost:8000/api',
    },
  },
});
