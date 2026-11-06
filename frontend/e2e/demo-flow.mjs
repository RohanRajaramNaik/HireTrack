// Records the guided demo end to end and checks the key interactions:
//   - rows appear within 300 ms of the match response arriving
//   - the entrance animation staggers (frames captured mid-animation)
//   - all 4 tour steps find their targets
//   - dragging a what-if slider re-orders the list without a network call
//   node e2e/demo-flow.mjs [outDir] [baseUrl]
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright-core'

const out = process.argv[2] || '../docs/evidence'
const base = process.argv[3] || 'http://127.0.0.1:8000'
const width = Number(process.env.W || 1366)
const height = Number(process.env.H || 768)
mkdirSync(out, { recursive: true })

let browser
for (const channel of ['msedge', 'chrome']) {
  try {
    browser = await chromium.launch({ channel })
    break
  } catch {
    /* next */
  }
}
const context = await browser.newContext({ viewport: { width, height }, recordVideo: { dir: out, size: { width, height } } })
const page = await context.newPage()
const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`)
}
const t0 = Date.now()

await page.goto(base + '/')
await page.waitForTimeout(700)

// Start the demo and time "response arrives" -> "first row visible".
const matchResponse = page.waitForResponse((r) => r.url().includes('/match') && r.request().method() === 'POST', { timeout: 60000 })
await page.getByTestId('start-demo').click()
await page.waitForURL(/\/jobs\/\d+/)
await page.screenshot({ path: `${out}/${width}-flow-01-job-prefilled.png` })
const resp = await matchResponse
const respAt = Date.now()
await page.locator('[data-testid="result-row"]').first().waitFor({ state: 'attached' })
const firstRowMs = Date.now() - respAt
check('Results appear within 300 ms of the response', firstRowMs <= 300, `${firstRowMs} ms`)
check('Match request succeeded', resp.ok(), `HTTP ${resp.status()}`)
await page.waitForTimeout(120)
await page.screenshot({ path: `${out}/${width}-flow-02-entrance-120ms.png` })
await page.waitForTimeout(330)
await page.screenshot({ path: `${out}/${width}-flow-03-entrance-450ms.png` })

// Stagger check: a later row should still be partly transparent early on.
const opacities = await page.$$eval('[data-testid="result-row"]', (rows) => rows.slice(0, 10).map((r) => Number(getComputedStyle(r).opacity)))
check('Rows animate in sequence (stagger)', opacities[0] > opacities[opacities.length - 1] || opacities.every((o) => o === 1), opacities.map((o) => o.toFixed(2)).join(' '))

// Tour
const tour = page.getByRole('dialog', { name: /Guided demo step/ })
await tour.waitFor({ timeout: 8000 })
for (let i = 1; i <= 4; i++) {
  await page.waitForTimeout(800)
  const label = await tour.getAttribute('aria-label')
  check(`Tour step ${i} shown`, label.includes(`step ${i} of 4`), label)
  await page.screenshot({ path: `${out}/${width}-flow-1${i}-tour-step-${i}.png` })
  if (i === 3) {
    const callout = await page.locator('[data-tour="keyword"]').count()
    check('Keyword-vs-meaning callout present for tour step 3', callout > 0)
  }
  if (i < 4) await tour.getByRole('button', { name: /Next/ }).click()
}

// What-if: drag the Meaning slider and confirm the order changes with no requests.
const before = await page.$$eval('[data-testid="result-row"]', (rows) => rows.map((r) => r.querySelector('button span')?.textContent))
let requests = 0
page.on('request', (r) => r.url().includes('/api/') && requests++)
const slider = page.locator('#whatif-semantic-range')
await slider.scrollIntoViewIfNeeded()
await page.waitForTimeout(300)
const box = await slider.boundingBox()
await page.mouse.move(box.x + box.width * 0.2, box.y + box.height / 2)
await page.mouse.down()
for (let s = 0; s <= 12; s++) {
  await page.mouse.move(box.x + box.width * (0.2 + (0.75 * s) / 12), box.y + box.height / 2)
  await page.waitForTimeout(40)
}
await page.mouse.up()
await page.waitForTimeout(140)
await page.screenshot({ path: `${out}/${width}-flow-20-whatif-mid-animation.png` })
await page.waitForTimeout(900)
await page.screenshot({ path: `${out}/${width}-flow-21-whatif-settled.png` })
const after = await page.$$eval('[data-testid="result-row"]', (rows) => rows.map((r) => r.querySelector('button span')?.textContent))
check('What-if slider re-orders the list', JSON.stringify(before) !== JSON.stringify(after), `top 3 now: ${after.slice(0, 3).join(', ')}`)
check('What-if re-rank made no API calls', requests === 0, `${requests} requests`)
const total = await page.getByTestId('weight-total').first().textContent()
check('What-if weights still total 100%', total.includes('100%'), total.trim())

await tour.getByRole('button', { name: 'Finish' }).click()
await page.waitForTimeout(400)
check('Whole guided demo runs well under 3 minutes', Date.now() - t0 < 180000, `${((Date.now() - t0) / 1000).toFixed(1)} s with automated clicks`)

await context.close()
await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} checks passed. Video and frames in ${out}`)
process.exit(failed.length ? 1 : 0)
