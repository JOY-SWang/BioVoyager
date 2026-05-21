import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// During dev (`bun run dev`), Vite serves the React app on :5173.
// Any path that the FastAPI backend owns is proxied through to 127.0.0.1:5000.
// In production, FastAPI serves ui/dist/ directly and no proxy is involved.
//
// Two macOS gotchas baked into the config:
//   - host '127.0.0.1' (not 'localhost') so Vite binds IPv4 — Apple Silicon
//     resolves localhost to ::1 only, breaking `curl 127.0.0.1`.
//   - proxy target 'http://127.0.0.1:5000' (not localhost) so we bypass
//     macOS's AirPlay Receiver, which steals ::1:5000 and returns 403.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/static': 'http://127.0.0.1:5000',
      '/raw': 'http://127.0.0.1:5000',
      '/view': 'http://127.0.0.1:5000',
      '/viewer': 'http://127.0.0.1:5000',
      '/export_pdf': 'http://127.0.0.1:5000',
    },
  },
})
