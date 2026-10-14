import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages 프로젝트 페이지 하위 경로
export default defineConfig({
  base: '/kbap-pm-agent/',
  plugins: [react()],
})
