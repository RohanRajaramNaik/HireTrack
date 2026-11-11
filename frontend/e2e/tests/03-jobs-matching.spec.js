import { writeFileSync } from 'node:fs'
import { expect, test } from '@playwright/test'
import { login, toast, uid } from './helpers'

test.describe('Job specifications and matching', () => {
  test('TC-09 create a job; Run Match stays locked until weights total 100%', async ({ page }) => {
    const title = `Python Developer ${uid()}`
    await login(page, 'recruiter')
    await page.goto('/jobs/new')
    await page.getByLabel('Job title').fill(title)
    await page.getByLabel('Location').fill('Cape Town')
    await page.getByLabel('Minimum years').fill('3')
    const req = page.getByLabel('Required skills', { exact: true })
    for (const s of ['Python', 'Django', 'SQL']) {
      await req.fill(s)
      await req.press('Enter')
    }
    await page
      .getByLabel('Job description')
      .fill('Build and maintain REST APIs in Python and Django with automated tests, code reviews and CI pipelines.')
    // Skills weight 40 -> 35 leaves the total at 95%.
    await page.getByLabel('Skills weight, percent').fill('35')
    await page.getByLabel('Skills weight, percent').blur()
    await expect(page.getByText('Run Match unlocks when the weights total exactly 100% (now 95%).')).toBeVisible()
    await expect(page.getByTestId('run-match')).toBeDisabled()
    await page.getByLabel('Skills weight, percent').fill('40')
    await page.getByLabel('Skills weight, percent').blur()
    await expect(page.getByTestId('run-match')).toBeEnabled()
    await page.getByRole('button', { name: 'Save job' }).click()
    await toast(page, 'Job saved')
    await expect(page.getByRole('link', { name: new RegExp(title) })).toBeVisible()
  })

  test('TC-10 run a match and read the score breakdown', async ({ page }) => {
    await login(page, 'recruiter')
    await page.goto('/jobs')
    await page.getByRole('link', { name: /Cloud Data Engineer/ }).click()
    await page.getByTestId('run-match').click()
    await expect(page.getByRole('heading', { name: 'Cloud Data Engineer' })).toBeVisible({ timeout: 45_000 })
    await expect(page.getByText(/6\d\d candidates ranked in/)).toBeVisible()
    const rows = page.locator('ol[aria-label="Ranked candidates"] > li')
    await expect(rows).toHaveCount(50)
    await rows.first().locator('button[aria-label^="Open breakdown"]').click()
    const panel = page.getByRole('dialog')
    await expect(panel.getByText('Exact calculation')).toBeVisible()
    await expect(panel.getByText(/Overall = \(.*\) \/ 100 = /)).toBeVisible()
    await expect(panel.getByText('Required skills')).toBeVisible()
  })

  test('TC-11 what-if weights re-rank without saving', async ({ page }) => {
    await login(page, 'recruiter')
    await page.goto('/results')
    await expect(page.getByRole('heading', { name: 'Cloud Data Engineer' })).toBeVisible()
    await page.getByRole('button', { name: 'What if' }).click()
    await page.getByLabel(/^Meaning.*weight, percent/).fill('60')
    await page.getByLabel(/^Meaning.*weight, percent/).blur()
    await expect(page.getByText('Showing what-if ranking')).toBeVisible()
  })

  test('TC-12 shortlist from results into the pipeline and export CSV', async ({ page }) => {
    await login(page, 'recruiter')
    await page.goto('/results')
    await expect(page.getByRole('heading', { name: 'Cloud Data Engineer' })).toBeVisible()
    const rows = page.locator('ol[aria-label="Ranked candidates"] > li')
    // pick the first two not already in the pipeline
    let picked = 0
    for (let i = 0; i < 15 && picked < 2; i++) {
      const row = rows.nth(i)
      if ((await row.locator('.chip').count()) === 0) {
        await row.getByRole('checkbox').check()
        picked++
      }
    }
    expect(picked).toBe(2)
    await page.getByRole('region', { name: 'Compare selection' }).getByRole('button', { name: 'Add to pipeline' }).click()
    await toast(page, '2 candidates added to the pipeline')

    // Capture the file at the last step instead of letting the browser save it.
    // (Under automation, Microsoft Edge keeps a finished blob download open and
    // the next test's browser context then hangs; Chrome does not. The app's
    // own code still runs in full: authenticated fetch, server file name, blob.)
    await page.evaluate(() => {
      window.__downloads = []
      const original = HTMLAnchorElement.prototype.click
      HTMLAnchorElement.prototype.click = function () {
        if (this.download) {
          const name = this.download
          window.__downloads.push(fetch(this.href).then((r) => r.text()).then((text) => ({ name, text })))
          return
        }
        return original.call(this)
      }
    })
    await page.getByRole('button', { name: 'Export CSV' }).click()
    await page.waitForFunction(() => window.__downloads.length === 1)
    const file = await page.evaluate(() => window.__downloads[0])
    expect(file.name).toMatch(/^hiretrack-cloud-data-engineer-\d{8}-\d{4}\.csv$/)
    expect(file.text).toContain('Rank,Candidate,Overall,Skills,Experience,Education,Semantic')
    expect(file.text.trim().split(/\r?\n/).length).toBeGreaterThan(600)
    writeFileSync(test.info().outputPath('results.csv'), file.text)
  })

  test('TC-13 performance: re-running a 600-candidate match takes under 5 seconds', async ({ page }) => {
    await login(page, 'recruiter')
    await page.goto('/results')
    await expect(page.getByRole('heading', { name: 'Cloud Data Engineer' })).toBeVisible()
    const started = Date.now()
    await page.getByRole('button', { name: 'Run Match again' }).click()
    await toast(page, 'Match complete')
    const seconds = (Date.now() - started) / 1000
    test.info().annotations.push({ type: 'timing', description: `600 candidates re-ranked end to end in ${seconds.toFixed(2)} s` })
    expect(seconds).toBeLessThan(5)
  })
})
