import { expect } from '@playwright/test'

export const ACCOUNTS = {
  admin: { email: 'admin@hiretrack.local', password: 'Admin@123', name: 'System Administrator' },
  recruiter: { email: 'recruiter@hiretrack.local', password: 'Recruiter@123', name: 'Nomvula Khumalo' },
  manager: { email: 'manager@hiretrack.local', password: 'Manager@123', name: 'Pieter Botha' },
}

/** Unique suffix so repeated runs never collide. */
export const uid = () => Date.now().toString(36).slice(-5)

export async function login(page, who = 'admin') {
  const a = ACCOUNTS[who]
  await page.goto('/')
  await page.getByLabel('Email').fill(a.email)
  await page.getByLabel('Password').fill(a.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
}

export async function signOut(page) {
  await page.getByRole('button', { name: /^Account:/ }).click()
  await page.getByRole('menuitem', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
}

/** Calls the API with the page's own sign-in token (for test set-up only). */
export async function apiAs(page, method, url, body) {
  return page.evaluate(
    async ({ method, url, body }) => {
      const r = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer ' + sessionStorage.getItem('hiretrack-token'),
        },
        body: body ? JSON.stringify(body) : undefined,
      })
      return { status: r.status, body: r.status === 204 ? null : await r.json() }
    },
    { method, url, body },
  )
}

export async function toast(page, text) {
  await expect(page.getByRole('status').filter({ hasText: text }).first()).toBeVisible()
}
