import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  const rootDir = path.resolve(__dirname, '..');
  const env = { ...loadEnv(mode, rootDir, ''), ...loadEnv(mode, process.cwd(), '') };
  const rawBackend = env.VITE_BACKEND_URL || env.BACKEND_URL || 'http://127.0.0.1:8000';

  let backendTarget = rawBackend.trim();
  if (!backendTarget.startsWith('http://') && !backendTarget.startsWith('https://')) {
    backendTarget = `http://${backendTarget}`;
  }
  const hostPart = backendTarget.slice(backendTarget.indexOf('://') + 3);
  if (!hostPart.includes(':')) {
    backendTarget = `${backendTarget}:8000`;
  }

  return {
    envDir: rootDir,
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3000,
      host: true,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    preview: {
      port: 3000,
      host: true,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
    },
  };
});
