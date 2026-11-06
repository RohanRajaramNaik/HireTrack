// Final end-to-end check through the real UI (app must be running on :8000):
// seed -> create job -> weights validation -> match -> results -> what-if ->
// CSV export -> backup -> restore -> candidate CRUD + validation -> guided demo.
//   HT_PASS=<passcode> node e2e/full-flow.mjs [outDir] [baseUrl]
import { mkdirSync, readFileSync } from 'node:fs'
import { chromium } from 'playwright-core'

const out = process.argv[2] || '../docs/evidence/final'
const base = process.argv[3] || 'http://127.0.0.1:8000'
const PASS = process.env.HT_PASS || 'hiretrack-demo'
mkdirSync(out, { recursive: true })
// playwright-core can reject an internal navigation promise when the browser closes; harmless.
process.on('unhandledRejection', (e) => {
  if (!String(e).includes('Target page, context or browser has been closed')) throw e
})

let browser
for (const channel of ['msedge', 'chrome']) {
  try {
    browser = await chromium.launch({ channel })
    break
  } catch {
    /* next */
  }
}
const context = await browser.newContext({ viewport: { width: 1366, height: 768 }, acceptDownloads: true })
const page = await context.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(e.message))
// 401s are expected: the first check deliberately uses a wrong passcode.
page.on('console', (m) => m.type() === 'error' && !m.text().includes('401') && errors.push(m.text()))
const results = []
const check = (name, ok, detail = '') => {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  (' + detail + ')' : ''}`)
}
const shot = (n) => page.screenshot({ path: `${out}/${n}.png` })

async function unlockAdmin() {
  await page.goto(base + '/admin')
  await page.getByLabel('Admin passcode').fill(PASS)
  await page.getByRole('button', { name: 'Unlock' }).click()
  await page.getByText('Admin tools unlocked').waitFor()
}

// 1. Seed via the Admin screen (with wrong passcode first)
await page.goto(base + '/admin')
await page.getByLabel('Admin passcode').fill('wrong-passcode')
await page.getByRole('button', { name: 'Unlock' }).click()
await page.getByText('Incorrect passcode').waitFor()
check('Admin rejects a wrong passcode', true)
await unlockAdmin()
await page.getByRole('button', { name: 'Load demo data' }).click()
await page.getByRole('button', { name: 'Replace data' }).click()
await page.getByText('Demo data loaded').waitFor({ timeout: 30000 })
check('Load demo data (with confirm dialog)', true)

// 2. Create a job; weights at 95% keep Run Match disabled
await page.goto(base + '/jobs/new')
await page.getByLabel('Job title').fill('Data Analyst')
await page.getByLabel('Minimum years').fill('2')
await page.getByLabel('Minimum education').selectOption({ label: "Bachelor's Degree" })
for (const s of ['Python', 'SQL']) {
  await page.getByLabel('Required skills', { exact: true }).fill(s)
  await page.getByLabel('Required skills', { exact: true }).press('Enter')
}
await page.getByRole('textbox', { name: /^Preferred skills/ }).fill('Power BI')
await page.getByRole('textbox', { name: /^Preferred skills/ }).press('Enter')
await page.getByLabel('Job description').fill('Analyse operational data with SQL and Python, build dashboards in Power BI and present findings to managers.')
await page.getByLabel('Meaning match weight, percent').fill('15')
const disabled = await page.getByTestId('run-match').isDisabled()
const warn = await page.getByText('Weights must add up to 100% (now 95%)').count()
check('Run Match disabled at 95% with the exact message', disabled && warn > 0)
await shot('01-weights-95')
await page.getByRole('button', { name: /Reset to defaults/ }).click()
check('Reset to defaults restores 100%', (await page.getByTestId('weight-total').textContent()).includes('100%'))
await page.getByRole('button', { name: 'Save job' }).click()
await page.getByText('Job saved').waitFor()
check('Save job', /\/jobs\/\d+$/.test(page.url()), page.url())

// 3. Run Match -> results
await page.getByTestId('run-match').click()
await page.waitForURL(/\/results\/\d+/, { timeout: 60000 })
await page.locator('[data-testid="result-row"]').first().waitFor()
const n = await page.locator('[data-testid="result-row"]').count()
check('Match runs and results render', n === 18, `${n} rows`)
await page.waitForTimeout(1500)
await shot('02-results')
const top = await page.locator('[data-testid="result-row"] button span').first().textContent()
check('Zanele Khumalo (data analyst) ranks first for Data Analyst', top === 'Zanele Khumalo', top)

// 4. Breakdown
await page.locator('[data-testid="result-row"] button').first().click()
const calc = await page.getByText(/^Overall = \(/).textContent()
check('Breakdown shows the exact calculation', /Overall = \(.+\) \/ 100 = \d+\.\d/.test(calc), calc)
await page.keyboard.press('Escape')

// 5. What-if drag
await page.getByRole('button', { name: /^What if/ }).click()
const before = await page.$$eval('[data-testid="result-row"] button span:first-child', (e) => e.map((x) => x.textContent))
const slider = page.locator('#whatif-experience-range')
await slider.scrollIntoViewIfNeeded()
const box = await slider.boundingBox()
await page.mouse.click(box.x + box.width * 0.95, box.y + box.height / 2)
await page.waitForTimeout(900)
const after = await page.$$eval('[data-testid="result-row"] button span:first-child', (e) => e.map((x) => x.textContent))
check('What-if re-ranks in the browser', JSON.stringify(before) !== JSON.stringify(after))
await shot('03-whatif')
await page.getByRole('button', { name: /Back to the run/ }).click()

// 6. CSV export
const [dl] = await Promise.all([page.waitForEvent('download'), page.getByRole('link', { name: /Export CSV/ }).click()])
const csvPath = `${out}/export.csv`
await dl.saveAs(csvPath)
const csv = readFileSync(csvPath, 'utf8').replace(/^﻿/, '').split(/\r?\n/).filter(Boolean)
check('Export CSV downloads all rows', csv[0].startsWith('Rank,Candidate,Overall') && csv.length === 19, `${csv.length - 1} rows, ${dl.suggestedFilename()}`)

// 7. Backup, change data, restore
await unlockAdmin()
await page.getByRole('button', { name: 'Back up now' }).click()
await page.getByText('Backup created').waitFor()
let firstFile = ''
for (let i = 0; i < 25 && !firstFile.endsWith('manual.db'); i++) {
  await page.waitForTimeout(200) // the list refreshes just after the toast
  firstFile = await page.locator('td .font-mono').first().textContent()
}
check('Back up now creates a backup', firstFile.endsWith('manual.db'), firstFile)
await page.request.post(`${base}/api/candidates`, {
  data: { full_name: 'Restore Marker', years_experience: 1, level_id: 1, resume_summary: 'Added after the backup, should disappear on restore.', skills: ['Excel'] },
})
await page.locator('tr', { hasText: firstFile }).getByRole('button', { name: 'Restore' }).click()
await page.getByLabel('Re-enter the admin passcode to confirm').fill(PASS)
await page.getByRole('button', { name: 'Restore backup' }).click()
await page.getByText('Backup restored').waitFor({ timeout: 30000 })
const marker = await (await page.request.get(`${base}/api/candidates?search=Restore%20Marker`)).json()
check('Restore brings back the earlier state', marker.total === 0, `marker rows after restore: ${marker.total}`)
await shot('04-admin-after-restore')

// 8. Candidate CRUD with validation
await page.goto(base + '/candidates')
await page.getByRole('button', { name: 'Add candidate' }).first().click()
await page.getByLabel('Full name').fill('Test Person')
await page.getByLabel('Years of experience').fill('-2')
await page.getByRole('button', { name: 'Add candidate' }).last().click()
const yrsErr = await page.getByText('Years of experience cannot be less than 0').count()
const sumErr = await page.getByText('Resume summary is required').count()
const skErr = await page.getByText('Add at least one skill').count()
check('Candidate form shows inline errors', yrsErr && sumErr && skErr, `years:${yrsErr} summary:${sumErr} skills:${skErr}`)
await shot('05-candidate-errors')
await page.getByLabel('Years of experience').fill('3')
await page.getByLabel('Highest education').selectOption({ label: 'Diploma' })
await page.getByLabel('Skills', { exact: true }).fill('JS')
await page.getByLabel('Skills', { exact: true }).press('Enter')
await page.getByLabel('Resume summary').fill('Builds small web tools in JavaScript for an operations team.')
await page.getByRole('button', { name: 'Add candidate' }).last().click()
await page.getByText('Candidate added').waitFor()
await page.getByLabel('Search candidates').fill('Test Person')
await page.waitForTimeout(300)
await page.getByRole('row', { name: /Test Person/ }).click()
await page.getByRole('button', { name: 'Delete', exact: true }).click()
await page.getByRole('button', { name: 'Delete candidate' }).click()
await page.getByText('Candidate deleted').waitFor()
check('Add, find and delete a candidate', true)

// 9. Guided demo
await page.goto(base + '/')
await page.getByTestId('start-demo').click()
await page.getByRole('dialog', { name: /Guided demo step 1 of 4/ }).waitFor({ timeout: 30000 })
check('Guided demo reaches the tour', true)
await shot('06-guided-demo')

await page.waitForTimeout(1500)
check('No browser console errors', errors.length === 0, errors.slice(0, 3).join(' | '))
await context.close()
await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} end-to-end checks passed`)
process.exit(failed.length ? 1 : 0)
