import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages 프로젝트 페이지 하위 경로 (ADR-5)
export default defineConfig({
  base: '/kbap-pm-agent/',
  plugins: [react()],
  // 미설정이어도 상수로 박아 운영 빌드에서 mock.ts가 트리셰이킹되게 한다 (check-f6이 확인)
  define: { 'import.meta.env.VITE_MOCK': JSON.stringify(process.env.VITE_MOCK ?? '') },
})
