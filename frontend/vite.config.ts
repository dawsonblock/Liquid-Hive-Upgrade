import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: process.env.NODE_ENV !== 'production',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-redux', '@mui/material', '@mui/icons-material'],
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target:
          process.env.VITE_BACKEND_URL ||
          process.env.REACT_APP_BACKEND_URL ||
          'http://localhost:8000',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, '/api'),
      },
      '/ws': {
        target: (
          process.env.VITE_BACKEND_URL ||
          process.env.REACT_APP_BACKEND_URL ||
          'http://localhost:8000'
        ).replace('http', 'ws'),
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
