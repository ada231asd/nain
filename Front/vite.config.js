import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [vue()],
    server: {
      proxy: {
        // Python backend serves API under /api. Default to 8000, override via VITE_PY_BACKEND_URL
        '/api': {
          target: env.VITE_PY_BACKEND_URL || 'http://192.168.10.39:8000',
          changeOrigin: true,
          secure: false,
          configure: (proxy, options) => {
            // Proxy event handlers configured silently
          }
        },
        // If later needed, you can add other proxies here
      }
    }
  }
})