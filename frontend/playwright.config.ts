import { createServer } from 'node:net'
import { defineConfig } from '@playwright/test'
import viteConfig from './vite.config.ts'

// 실행마다 빈 포트로 새 dev 서버를 띄움. 고정 포트 재사용은 동시 실행 시 다른 트리(미커밋 코드)의 서버를 검사하게 됨
// 워커 프로세스도 설정을 다시 읽으므로 처음 정한 포트를 환경변수로 넘겨 같은 서버를 보게 함
function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer().listen(0, () => {
      const addr = srv.address()
      srv.close(() => (addr && typeof addr === 'object' ? resolve(addr.port) : reject(new Error('빈 포트 없음'))))
    })
  })
}
process.env.UI_PORT ??= String(await freePort())
const PORT = Number(process.env.UI_PORT)
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
    reuseExistingServer: false,
    // 고정 응답 모드에서는 page.route가 가로채고, live 모드에서는 로컬 백엔드로
    env: { VITE_API_BASE_URL: process.env.VITE_API_BASE_URL ?? 'http://localhost:8000' },
  },
})
