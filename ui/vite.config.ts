import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const apiTarget = process.env.NETWORK_PICASSO_API_TARGET || 'http://127.0.0.1:8787';
const uiPort = Number(process.env.NETWORK_PICASSO_UI_PORT || 5173);

export default defineConfig({
  plugins: [react()],
  server: {
    port: uiPort,
    strictPort: true,
    proxy: {
      '/api': apiTarget,
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
