import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Local dev: backend on localhost. Docker uses nginx (see nginx.conf), not this proxy.
      '/api': 'http://localhost:8000'
    }
  }
})
