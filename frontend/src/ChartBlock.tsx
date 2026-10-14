import { useEffect, useRef } from 'react'
import {
  BarController, BarElement, CategoryScale, Chart, Legend, LinearScale, LineController, LineElement, PointElement, Title, Tooltip,
} from 'chart.js'
import type { ChartSpec } from './chartBlock.ts'

// 선·막대에 필요한 부분만 등록해 번들 크기 제한
Chart.register(LineController, BarController, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Legend, Tooltip, Title)

// 차트 색은 디자인 토큰에서만 읽음, 토큰이 없으면 Chart.js 기본값
function tokens() {
  const css = getComputedStyle(document.documentElement)
  const v = (name: string) => css.getPropertyValue(name).trim() || undefined
  return {
    text: v('--color-text'),
    grid: v('--chart-grid') ?? v('--color-border'),
    series: [v('--chart-1'), v('--chart-2'), v('--chart-3'), v('--chart-4')],
  }
}

function applyColors(chart: Chart, spec: ChartSpec) {
  const t = tokens()
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
  chart.update(spec.x.length > 100 ? 'none' : undefined)
}

export default function ChartBlock({ spec }: { spec: ChartSpec }) {
  const canvas = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvas.current) return
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    const chart = new Chart(canvas.current, {
      type: spec.type,
      data: {
        labels: spec.x,
        datasets: spec.series.map((s) => ({ label: s.name, data: s.values, spanGaps: false })),
      },
      options: {
        responsive: true,
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
    return () => {
      mq.removeEventListener('change', onTheme)
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
