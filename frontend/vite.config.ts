import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// For development on laptop while API runs on Pi
// Usage: npm run dev:pi -- --host <pi-ip>
const PI_HOST = process.env.PI_HOST || '192.168.1.9'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: `http://${PI_HOST}:8000`,
        changeOrigin: true,
      },
      '/stream.mjpg': {
        target: `http://${PI_HOST}:8000`,
        changeOrigin: true,
        ws: true,
      },
    },
  },
})