import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Grab the port from process.env (injected by Docker Compose), defaulting to 3000 if not found
  const port = parseInt(process.env.FRONTEND_PORT) || 3000;

  return {
    plugins: [react()],
    server: {
      host: true, // Needed for Docker so it binds to 0.0.0.0 instead of localhost
      port: port,
    },
  }
})
