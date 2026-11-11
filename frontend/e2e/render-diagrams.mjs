// Render docs/diagrams/*.svg to PNG at 2x scale for the report.
//   node e2e/render-diagrams.mjs
import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const dir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/diagrams')
const browser = await chromium.launch({ channel: 'msedge' }).catch(() => chromium.launch({ channel: 'chrome' }))
for (const f of readdirSync(dir).filter((n) => n.endsWith('.svg'))) {
  const svg = readFileSync(path.join(dir, f), 'utf-8')
  const [, w, h] = svg.match(/width="(\d+)" height="(\d+)"/)
  const page = await browser.newPage({ viewport: { width: Number(w), height: Number(h) }, deviceScaleFactor: 2 })
  await page.setContent(`<html><body style="margin:0">${svg}</body></html>`)
  await page.screenshot({ path: path.join(dir, f.replace('.svg', '.png')), clip: { x: 0, y: 0, width: Number(w), height: Number(h) } })
  await page.close()
  console.log('rendered', f)
}
await browser.close()
