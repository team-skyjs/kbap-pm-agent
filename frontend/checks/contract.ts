// 계약서 분할본(specs/.../contracts/*.md)의 코드 블록을 원문 그대로 꺼낸다. 예시를 손으로 베끼지 않기 위함.
import { readFileSync } from 'node:fs'

const DIR = new URL('../../specs/001-pm-agent-prototype/contracts/', import.meta.url)

export function blocks(file: string): string[] {
  const md = readFileSync(new URL(file, DIR), 'utf8')
  return [...md.matchAll(/^```[a-z]*\n([\s\S]*?)^```/gm)].map((m) => m[1])
}
export const jsonBlock = (file: string, i: number): unknown => JSON.parse(blocks(file)[i])
