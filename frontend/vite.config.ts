import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 개발 서버도 운영과 같은 출처 구조: /api를 로컬 백엔드로 프록시
export default defineConfig({
  base: '/',
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
