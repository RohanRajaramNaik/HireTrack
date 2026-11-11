import { expect, test } from '@playwright/test'
import { login, signOut, toast, uid } from './helpers'

test.describe('Dashboard and administration', () => {
  test('TC-20 dashboard shows the key counts and charts', async ({ page }) => {
    await login(page, 'admin')
    const figures = page.getByRole('region', { name: 'Key figures' })
    await expect(figures.getByText('Candidates')).toBeVisible()
    await expect(figures.getByText('Open jobs')).toBeVisible()
    await expect(figures.getByText('Applications in progress')).toBeVisible()
    await expect(figures.getByText('Staff utilisation')).toBeVisible()
    for (const title of ['Hiring pipeline', 'Staff by utilisation today', 'Open jobs with the most applicants', 'Hires per month', 'Recent pipeline activity']) {
      await expect(page.getByRole('heading', { name: title })).toBeVisible()
    }
    // Selecting a utilisation band opens the filtered staff list.
    await page.getByRole('button', { name: /Bench \(0%\)/ }).click()
    await expect(page).toHaveURL(/\/resources\?band=bench/)
  })

  test('TC-21 an administrator creates a user who can then sign in', async ({ page }) => {
    const email = `hr.${uid()}@hiretrack.local`
    await login(page, 'admin')
    await page.goto('/admin')
    await page.getByRole('button', { name: 'Add user' }).click()
    const panel = page.getByRole('dialog')
    await panel.getByLabel('Full name').fill('New Recruiter')
    await panel.getByLabel('Email').fill(email)
    await panel.getByLabel('Role').selectOption('recruiter')
    await panel.getByLabel('Password').fill('Welcome123')
    await panel.getByRole('button', { name: 'Create user' }).click()
    await toast(page, 'User created')
    await signOut(page)
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill('Welcome123')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('button', { name: 'Account: New Recruiter' })).toBeVisible()
  })

  test('TC-22 manual backup, and data reset needs the admin password', async ({ page }) => {
    await login(page, 'admin')
    await page.goto('/admin')
    await page.getByRole('button', { name: 'Back up now' }).click()
    await toast(page, 'Backup created')
    await expect(page.getByRole('cell', { name: /Manual/ }).first()).toBeVisible()

    await page.getByRole('button', { name: 'Load demo set' }).click()
    const dialog = page.getByRole('alertdialog')
    await dialog.getByLabel('Your password').fill('wrong-password1')
    await dialog.getByRole('button', { name: 'Replace data' }).click()
    await expect(dialog.getByText('Incorrect password')).toBeVisible()
    await dialog.getByRole('button', { name: 'Cancel' }).click()
    // Nothing was replaced.
    await page.goto('/candidates')
    await expect(page.getByText(/60\d candidates in the database/)).toBeVisible()
  })
})
