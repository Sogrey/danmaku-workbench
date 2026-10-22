import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// dev 端口 8312：对齐课程原版工作台地址 localhost:8312
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 8312,
    proxy: {
      // 决策服务（后续接入真实模型时由 FastAPI 提供 /api/decide）
      '/api': {
        target: 'http://127.0.0.1:8313',
        changeOrigin: true,
      },
    },
  },
})
