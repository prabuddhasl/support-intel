import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/tickets': process.env.API_URL ?? 'http://localhost:8000',
      '/analytics': process.env.API_URL ?? 'http://localhost:8000',
      '/categories': process.env.API_URL ?? 'http://localhost:8000',
      '/sentiments': process.env.API_URL ?? 'http://localhost:8000',
      '/health': process.env.API_URL ?? 'http://localhost:8000',
    },
  },
})
