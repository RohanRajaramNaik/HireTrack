import { expect, test } from '@playwright/test'
import { apiAs, login, toast, uid } from './helpers'

test.describe('Applicant pipeline', () => {
  test('TC-14 move an applicant from Applied to Hired with notes; hire joins the staff pool', async ({ page }) => {
    await login(page, 'recruiter')
    // Set-up: a fresh candidate applied to an open job.
    const name = `Pipeline Person ${uid()}`
    const cand = await apiAs(page, 'POST', '/api/candidates', {
      full_name: name,
      years_experience: 5,
      level_id: 4,
      location: 'Johannesburg',
      resume_summary: 'Cloud engineer who builds AWS landing zones with Terraform and supports Linux servers.',
      skills: ['AWS', 'Terraform', 'Linux'],
    })
    const jobs = (await apiAs(page, 'GET', '/api/jobs')).body
    const job = jobs.find((j) => j.job_title === 'Cloud Engineer')
    await apiAs(page, 'POST', '/api/applications', { candidate_id: cand.body.candidate_id, job_id: job.job_id })

    await page.goto(`/pipeline/${job.job_id}`)
    await page.getByRole('region', { name: /^Applied/ }).getByText(name).click()
    const panel = page.getByRole('dialog')
    const steps = [
      ['Mark as screened', 'Screened', 'CV meets requirements'],
      ['Move to interview', 'Interview', 'Technical interview booked'],
      ['Make an offer', 'Offer', 'Offer sent'],
      ['Mark as hired', 'Hired', 'Offer accepted'],
    ]
    for (const [button, stage, note] of steps) {
      await panel.getByLabel(/Note for the next change/).fill(note)
      await panel.getByRole('button', { name: button }).click()
      await expect(panel.getByText('Current stage')).toBeVisible()
      await expect(panel.locator('p.text-lg', { hasText: stage })).toBeVisible()
    }
    await expect(panel.getByText('Offer accepted')).toBeVisible()
    await expect(panel.getByText(/is in the staff pool/)).toBeVisible()
    await expect(panel.locator('ol li')).toHaveCount(5) // full audit history
    await page.keyboard.press('Escape')
    await expect(page.getByRole('region', { name: /^Hired/ }).getByText(name)).toBeVisible()

    await page.goto('/resources')
    await page.getByLabel('Search staff').fill(name)
    const row = page.getByRole('row').filter({ hasText: name })
    await expect(row).toHaveCount(1)
    await expect(row.getByRole('cell', { name: 'Cloud Engineer' })).toBeVisible()
    await expect(row.getByRole('cell', { name: 'Hired', exact: true })).toBeVisible()
  })

  test('TC-15 stages cannot be skipped; a rejection can be reopened', async ({ page }) => {
    await login(page, 'recruiter')
    const apps = (await apiAs(page, 'GET', '/api/applications?stage=applied')).body
    const app = apps[0]
    // The API refuses a skipped stage.
    const skip = await apiAs(page, 'POST', `/api/applications/${app.application_id}/stage`, { stage: 'offer' })
    expect(skip.status).toBe(422)
    expect(skip.body.detail).toContain('next stage is Screened')

    await page.goto(`/pipeline/${app.job_id}`)
    await page.getByRole('region', { name: /^Applied/ }).getByText(app.candidate_name).first().click()
    const panel = page.getByRole('dialog')
    await panel.getByLabel(/Note for the next change/).fill('Missing required skills')
    await panel.getByRole('button', { name: 'Reject' }).click()
    await expect(panel.locator('p.text-lg', { hasText: 'Rejected' })).toBeVisible()
    await panel.getByRole('button', { name: 'Reopen at Applied' }).click()
    await expect(panel.locator('p.text-lg', { hasText: 'Applied' })).toBeVisible()
    await expect(panel.getByText('Missing required skills')).toBeVisible()
  })

  test('TC-16 a resource manager can view the pipeline but not change it', async ({ page }) => {
    await login(page, 'manager')
    await page.goto('/pipeline')
    await expect(page.getByTestId('pipeline-board')).toBeVisible()
    await page.getByTestId('pipeline-card').first().click()
    const panel = page.getByRole('dialog')
    await expect(panel.getByText('History')).toBeVisible()
    await expect(panel.getByRole('button', { name: /Mark as|Move to|Make an offer|Reject/ })).toHaveCount(0)
  })
})
