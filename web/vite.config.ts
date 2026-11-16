import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Dev: /v1 is proxied to the API on :8100, so the browser sees one origin.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/v1': 'http://localhost:8100', '/health': 'http://localhost:8100' } },
})
