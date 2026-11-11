import { expect, test } from '@playwright/test'
import { ACCOUNTS, login, signOut } from './helpers'

test.describe('Sign-in and role-based access', () => {
  test('TC-01 wrong password is rejected with a clear message', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel('Email').fill(ACCOUNTS.admin.email)
    await page.getByLabel('Password').fill('not-the-password1')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByText('Incorrect email or password')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toHaveCount(0)
  })

  test('TC-02 each role signs in and sees only its menu items', async ({ page }) => {
    const expected = {
      admin: ['Dashboard', 'Candidates', 'Jobs', 'Matching', 'Pipeline', 'Resources', 'Admin'],
      recruiter: ['Dashboard', 'Candidates', 'Jobs', 'Matching', 'Pipeline', 'Resources'],
      manager: ['Dashboard', 'Candidates', 'Jobs', 'Pipeline', 'Resources'],
    }
    for (const who of Object.keys(expected)) {
      await login(page, who)
      await expect(page.getByRole('button', { name: `Account: ${ACCOUNTS[who].name}` })).toBeVisible()
      const links = await page.getByRole('navigation', { name: 'Main' }).first().getByRole('link').allTextContents()
      expect(links).toEqual(expected[who])
      await signOut(page)
    }
  })

  test('TC-03 a recruiter opening the Admin URL directly is refused', async ({ page }) => {
    await login(page, 'recruiter')
    await page.goto('/admin')
    await expect(page.getByText('You do not have access to this page')).toBeVisible()
    // The API refuses too, even without the screen.
    const status = await page.evaluate(async () => {
      const r = await fetch('/api/users', { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('hiretrack-token') } })
      return r.status
    })
    expect(status).toBe(403)
  })

  test('TC-04 signing out ends the session', async ({ page }) => {
    await login(page, 'manager')
    await signOut(page)
    await page.goto('/resources')
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  })
})
