// Screenshot every screen at 1366x768 and 1920x1080 for design review.
//   node e2e/screens.mjs [outDir] [baseUrl]
// Uses the locally installed Microsoft Edge (or Chrome) through playwright-core,
// so no browser download is needed. Output folder is gitignored.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright-core'

const out = process.argv[2] || '../docs/screenshots'
const base = process.argv[3] || 'http://127.0.0.1:8000'
mkdirSync(out, { recursive: true })

async function launch() {
  for (const channel of ['msedge', 'chrome']) {
    try {
      return await chromium.launch({ channel })
    } catch {
      /* try next */
    }
  }
  throw new Error('Neither Edge nor Chrome found')
}

const browser = await launch()
const sizes = [
  [1366, 768],
  [1920, 1080],
]
const wait = (p, ms) => p.waitForTimeout(ms)

for (const [w, h] of sizes) {
  const page = await browser.newPage({ viewport: { width: w, height: h } })
  const shot = (name, full = false) => page.screenshot({ path: `${out}/${w}-${name}.png`, fullPage: full })
  const jobs = await (await page.request.get(`${base}/api/jobs`)).json()
  const cde = jobs.find((j) => j.job_title === 'Cloud Data Engineer') || jobs[0]

  await page.goto(base + '/')
  await wait(page, 900)
  await shot('01-dashboard')

  await page.goto(base + '/candidates')
  await wait(page, 900)
  await shot('02-candidates')
  await page.getByRole('row').nth(1).click()
  await wait(page, 600)
  await shot('03-candidate-form')
  await page.keyboard.press('Escape')

  await page.goto(`${base}/jobs/${cde.job_id}`)
  await wait(page, 900)
  await shot('04-job-form')
  await shot('04b-job-form-full', true)

  await page.goto(`${base}/results/${cde.job_id}`)
  await wait(page, 2200)
  await shot('05-results')
  await page.getByRole('button', { name: /Explain this ranking/ }).click()
  await wait(page, 500)
  await shot('06-results-explain')
  await page.getByRole('button', { name: /Explain this ranking/ }).click()

  await page.getByRole('button', { name: /^What if/ }).click()
  await wait(page, 500)
  await page.locator('#whatif-semantic-range').fill('70')
  await wait(page, 900)
  await shot('07-results-whatif')
  await page.getByRole('button', { name: /Back to the run/ }).click()
  await page.getByRole('button', { name: /^What if/ }).click()
  await wait(page, 400)

  await page.locator('[data-testid="result-row"] button').first().click()
  await wait(page, 900)
  await shot('08-breakdown')
  await page.keyboard.press('Escape')
  await wait(page, 300)

  const boxes = page.getByRole('checkbox')
  await boxes.nth(0).check()
  await boxes.nth(1).check()
  await boxes.nth(2).check()
  await page.getByRole('button', { name: /head to head/ }).click()
  await wait(page, 900)
  await shot('09-compare')
  await page.keyboard.press('Escape')

  await page.goto(base + '/admin')
  await wait(page, 600)
  await shot('10-admin-locked')
  await page.getByLabel('Admin passcode').fill(process.env.HT_PASS || 'hiretrack-demo')
  await page.getByRole('button', { name: 'Unlock' }).click()
  await wait(page, 900)
  await shot('11-admin')

  await page.goto(base + '/jobs/new')
  await wait(page, 700)
  await page.getByRole('button', { name: 'Save job' }).click()
  await wait(page, 400)
  await shot('12-job-validation')
  await page.close()
}

// Dark theme check at the presenter resolution
const dark = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
await dark.addInitScript(() => localStorage.setItem('hiretrack-theme', 'dark'))
const jobs = await (await dark.request.get(`${base}/api/jobs`)).json()
await dark.goto(`${base}/results/${(jobs.find((j) => j.job_title === 'Cloud Data Engineer') || jobs[0]).job_id}`)
await dark.waitForTimeout(2200)
await dark.screenshot({ path: `${out}/1920-13-results-dark.png` })
await browser.close()
console.log('Screenshots written to', out)
