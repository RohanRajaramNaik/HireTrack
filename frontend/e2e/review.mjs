// Screenshot every main screen for each role (design review and the report).
//   node e2e/review.mjs <outDir> [baseUrl] [width] [height]
// Uses the installed Edge or Chrome through playwright-core (no browser download).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright-core'

const out = process.argv[2] || '../docs/screenshots'
const base = process.argv[3] || 'http://127.0.0.1:8000'
const W = Number(process.argv[4] || 1366)
const H = Number(process.argv[5] || 768)
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
const page = await browser.newPage({ viewport: { width: W, height: H } })
const shot = (name, full = false) => page.screenshot({ path: `${out}/${name}.png`, fullPage: full })
const settle = (ms = 900) => page.waitForTimeout(ms)

async function login(email, password) {
  await page.goto(base + '/')
  await page.evaluate(() => sessionStorage.clear())
  await page.goto(base + '/')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByRole('heading', { name: 'Dashboard' }).waitFor()
  await settle(1200)
}

await page.goto(base + '/')
await page.getByRole('button', { name: 'Demo accounts' }).click()
await settle(300)
await shot('01-login')

await login('admin@hiretrack.local', 'Admin@123')
await shot('02-dashboard', true)

await page.goto(base + '/candidates')
await settle()
await shot('03-candidates')
await page.getByRole('button', { name: 'Add candidate' }).first().click()
await settle(500)
await shot('04-candidate-form')
await page.keyboard.press('Escape')
await page.getByRole('button', { name: 'Import CSV or Excel' }).click()
await settle(500)
await shot('05-import')
await page.keyboard.press('Escape')

await page.goto(base + '/jobs')
await settle(1200)
await shot('06-job-spec')

await page.goto(base + '/results')
await settle(2500)
await shot('07-matching-results')
await page.locator('ol[aria-label="Ranked candidates"] li button').first().click()
await settle(900)
await shot('08-score-breakdown')
await page.keyboard.press('Escape')

await page.goto(base + '/pipeline')
await settle(1500)
await shot('09-pipeline-all')
const jobs = await page.evaluate(async () => {
  const r = await fetch('/api/jobs', { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('hiretrack-token') } })
  return r.json()
})
const busy = jobs.find((j) => j.job_title === 'Cloud Engineer') || jobs[0]
await page.goto(`${base}/pipeline/${busy.job_id}`)
await settle(1200)
await shot('10-pipeline-job')
await page.getByTestId('pipeline-card').first().click()
await settle(900)
await shot('11-application-detail')
await page.keyboard.press('Escape')

await page.goto(base + '/resources')
await settle(1200)
await shot('12-staff')
await page.goto(base + '/resources/projects')
await settle(1000)
await shot('13-projects')
await page.getByRole('button', { name: 'Core Banking Data Migration' }).click()
await settle(1000)
await shot('14-project-detail')
await page.keyboard.press('Escape')

await page.goto(base + '/admin')
await settle(1000)
await shot('15-admin', true)

await login('manager@hiretrack.local', 'Manager@123')
await shot('16-dashboard-resource-manager')
await page.goto(base + '/results')
await settle(600)
await shot('17-access-denied')

await login('recruiter@hiretrack.local', 'Recruiter@123')
await page.goto(base + '/resources')
await settle(1000)
await shot('18-resources-recruiter-readonly')

await browser.close()
console.log('Screenshots written to', out)
