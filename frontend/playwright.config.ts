import { defineConfig } from '@playwright/test'
import viteConfig from './vite.config.ts'

// 다른 워크트리의 dev 서버(5173)를 잘못 재사용하지 않게 전용 포트
const PORT = Number(process.env.UI_PORT ?? 5183)
const BASE_PATH = typeof viteConfig === 'object' && 'base' in viteConfig && typeof viteConfig.base === 'string' ? viteConfig.base : '/'

const viewports = [
  { name: '1280', width: 1280, height: 800 },
  { name: '768', width: 768, height: 1024 },
  { name: '375', width: 375, height: 812 },
]
const modes = [
  { name: 'light', colorScheme: 'light', reducedMotion: 'no-preference' },
  { name: 'dark', colorScheme: 'dark', reducedMotion: 'no-preference' },
  { name: 'reduced', colorScheme: 'light', reducedMotion: 'reduce' },
] as const

export default defineConfig({
  testDir: 'checks/ui',
  outputDir: 'test-results',
  reporter: [['list']],
  use: { baseURL: `http://localhost:${PORT}${BASE_PATH}`, browserName: 'chromium' },
  projects: viewports.flatMap((v) => modes.map((m) => ({
    name: `${v.name}-${m.name}`,
    use: { viewport: { width: v.width, height: v.height }, colorScheme: m.colorScheme, reducedMotion: m.reducedMotion },
  }))),
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}${BASE_PATH}`,
    reuseExistingServer: true,
    // 고정 응답 모드에서는 page.route가 가로채고, live 모드에서는 로컬 백엔드로
    env: { VITE_API_BASE_URL: process.env.VITE_API_BASE_URL ?? 'http://localhost:8000' },
  },
})
