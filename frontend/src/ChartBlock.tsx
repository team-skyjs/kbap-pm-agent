import { useEffect, useRef } from 'react'
import {
  BarController, BarElement, CategoryScale, Chart, Legend, LinearScale, LineController, LineElement, PointElement, Title, Tooltip,
} from 'chart.js'
import type { ChartSpec } from './chartBlock.ts'

// 선·막대에 필요한 부분만 등록해 번들 크기 제한
Chart.register(LineController, BarController, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Legend, Tooltip, Title)

// A4 세로에서 인쇄 여백을 뺀 본문 폭 근사. 인쇄 미리보기는 캔버스를 다시 그리지 않아 이 폭으로 미리 그림
const PRINT_WIDTH = 680

// 차트 색은 디자인 토큰에서만 읽음, 토큰이 없으면 Chart.js 기본값
// 인쇄 직전에도 화면 매체 값이 읽히므로 인쇄는 항상 밝은 --print-* 토큰을 씀
function tokens(print = false) {
  const css = getComputedStyle(document.documentElement)
  const v = (name: string) => css.getPropertyValue(name).trim() || undefined
  if (print) {
    return {
      font: v('--font-sans'),
      text: v('--print-text'),
      grid: v('--print-grid'),
      series: [v('--print-chart-1'), v('--print-chart-2'), v('--print-chart-3'), v('--print-chart-4')],
    }
  }
  return {
    font: v('--font-sans'),
    text: v('--color-text'),
    grid: v('--chart-grid') ?? v('--color-border'),
    series: [v('--chart-1'), v('--chart-2'), v('--chart-3'), v('--chart-4')],
  }
}

function paint(chart: Chart, print: boolean) {
  const t = tokens(print)
  chart.data.datasets.forEach((ds, i) => {
    const c = t.series[i]
    ds.borderColor = c
    ds.backgroundColor = c
  })
  const o = chart.options
  if (o.plugins?.legend?.labels) o.plugins.legend.labels.color = t.text
  if (o.plugins?.title) o.plugins.title.color = t.text
  for (const axis of ['x', 'y'] as const) {
    const scale = o.scales?.[axis]
    if (!scale) continue
    if (scale.ticks) scale.ticks.color = t.text
    if (scale.grid) scale.grid.color = t.grid
  }
}

function applyColors(chart: Chart, spec: ChartSpec) {
  paint(chart, false)
  chart.update(spec.x.length > 100 ? 'none' : undefined)
}

export default function ChartBlock({ spec }: { spec: ChartSpec }) {
  const canvas = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvas.current) return
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    // 본문 한글과 같은 글꼴
    const font = tokens().font
    if (font) Chart.defaults.font.family = font
    const chart = new Chart(canvas.current, {
      type: spec.type,
      data: {
        labels: spec.x,
        datasets: spec.series.map((s) => ({ label: s.name, data: s.values, spanGaps: false })),
      },
      options: {
        responsive: true,
        // 높이는 컨테이너가 예약(로딩 전환 시 점프 방지), 폭은 본문을 채우도록 비율 고정 해제
        maintainAspectRatio: false,
        animation: reduce ? false : undefined,
        interaction: { mode: 'index', intersect: false },
        plugins: { title: { display: true, text: spec.title }, legend: { display: true, labels: {} }, tooltip: { enabled: true } },
        // 긴 수열은 축 라벨 자동 생략으로 겹침 방지
        scales: { x: { ticks: { autoSkip: true, maxRotation: 0 }, grid: {} }, y: { ticks: {}, grid: {} } },
      },
    })
    applyColors(chart, spec)
    // 화면을 연 채 테마가 바뀌면 토큰 색을 다시 읽음
    const mq = matchMedia('(prefers-color-scheme: dark)')
    const onTheme = () => applyColors(chart, spec)
    mq.addEventListener('change', onTheme)

    // 인쇄 직전: 애니메이션 없이 밝은 색·인쇄 폭으로 다시 그림, 직후: 화면 색·원래 설정·컨테이너 크기로 복원
    const screenAnimation = chart.options.animation
    let printing = false
    const onBeforePrint = () => {
      if (printing) return
      printing = true
      // 애니메이션 중에는 크기 변경이 다음 그리기로 미뤄지므로 먼저 멈추고, 미뤄져 있던 크기 변경은 update로 먼저 비운 뒤
      // 마지막에 인쇄 폭으로 맞춤(순서가 바뀌면 남아 있던 컨테이너 폭이 덮어씀)
      chart.stop()
      chart.options.animation = false
      paint(chart, true)
      chart.update('none')
      chart.resize(PRINT_WIDTH, chart.height)
    }
    const restoreScreen = () => {
      printing = false
      chart.options.animation = screenAnimation
      paint(chart, false)
      chart.resize()
      chart.update('none')
    }
    const onAfterPrint = () => { if (printing) restoreScreen() }
    const mqPrint = matchMedia('print')
    // afterprint가 인쇄 매체가 남아 있는 동안 오면 인쇄용 색을 읽으므로, 화면 매체로 돌아오면 항상 화면 색으로 다시 칠함
    const onPrintMedia = (e: MediaQueryListEvent) => (e.matches ? onBeforePrint() : restoreScreen())
    addEventListener('beforeprint', onBeforePrint)
    addEventListener('afterprint', onAfterPrint)
    mqPrint.addEventListener('change', onPrintMedia)
    return () => {
      mq.removeEventListener('change', onTheme)
      removeEventListener('beforeprint', onBeforePrint)
      removeEventListener('afterprint', onAfterPrint)
      mqPrint.removeEventListener('change', onPrintMedia)
      chart.destroy()
    }
  }, [spec])

  return (
    <figure className="md-chart">
      <div role="img" aria-label={spec.title}>
        <canvas ref={canvas} aria-hidden="true" />
      </div>
      <table className="visually-hidden">
        <caption>{spec.title}</caption>
        <thead>
          <tr><th scope="col">항목</th>{spec.series.map((s) => <th key={s.name} scope="col">{s.name}</th>)}</tr>
        </thead>
        <tbody>
          {spec.x.map((label, i) => (
            <tr key={i}>
              <th scope="row">{label}</th>
              {spec.series.map((s) => <td key={s.name}>{s.values[i] ?? '값 없음'}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}
