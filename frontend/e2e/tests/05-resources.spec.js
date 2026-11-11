import { expect, test } from '@playwright/test'
import { login, toast, uid } from './helpers'

/** Select the <option> whose text starts with `text` (selectOption needs an exact value). */
async function choose(select, text) {
  const value = await select.locator('option', { hasText: text }).first().getAttribute('value')
  await select.selectOption(value)
}

const iso = (days) => {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

test.describe('Resource allocation', () => {
  test('TC-17 create a project, allocate staff, and block over-allocation', async ({ page }) => {
    const project = `Payments API ${uid()}`
    const person = `Bench Person ${uid()}`
    await login(page, 'manager')
    await page.goto('/resources')

    // A new staff member starts on the bench at 0%.
    await page.getByRole('button', { name: 'Add staff member' }).click()
    let panel = page.getByRole('dialog')
    await panel.getByLabel('Full name').fill(person)
    await panel.getByLabel('Role').fill('Software Developer')
    await panel.getByRole('button', { name: 'Add staff member' }).click()
    await toast(page, 'Staff member added')

    await page.goto('/resources/projects')
    await page.getByRole('button', { name: 'New project' }).click()
    panel = page.getByRole('dialog')
    await panel.getByLabel('Project name').fill(project)
    await panel.getByLabel('Client').fill('Karoo Mutual Bank')
    await panel.getByLabel('Start').first().fill(iso(-7))
    await panel.getByLabel('End').first().fill(iso(120))
    await panel.getByLabel('Status').selectOption('active')
    await panel.getByRole('button', { name: 'Create project' }).click()
    await toast(page, 'Project created')

    const form = panel.getByTestId('allocation-form')
    await choose(form.getByLabel('Staff member'), person)
    await form.getByLabel('Allocation %').fill('70')
    await form.getByRole('button', { name: 'Save allocation' }).click()
    await toast(page, 'Allocation saved')
    await expect(panel.getByText('0.7 full-time equivalent today')).toBeVisible()

    // A second 50% booking on the same dates would be 120%: refused.
    await choose(form.getByLabel('Staff member'), person)
    await form.getByLabel('Allocation %').fill('50')
    await form.getByRole('button', { name: 'Save allocation' }).click()
    await expect(form.getByText(/most you can add for these dates is 30%/)).toBeVisible()

    await page.keyboard.press('Escape')
    await page.goto('/resources')
    await page.getByLabel('Search staff').fill(person)
    const row = page.getByRole('row').filter({ hasText: person })
    await expect(row.getByText('70%')).toBeVisible()
    await expect(row.getByRole('cell', { name: project })).toBeVisible()
  })

  test('TC-18 project end date before the start date is refused', async ({ page }) => {
    await login(page, 'manager')
    await page.goto('/resources/projects')
    await page.getByRole('button', { name: 'New project' }).click()
    const panel = page.getByRole('dialog')
    await panel.getByLabel('Project name').fill(`Bad Dates ${uid()}`)
    await panel.getByLabel('Client').fill('Test Client')
    await panel.getByLabel('Start').first().fill(iso(30))
    await panel.getByLabel('End').first().fill(iso(1))
    await panel.getByRole('button', { name: 'Create project' }).click()
    await expect(panel.getByText('End date cannot be before the start date')).toBeVisible()
  })

  test('TC-19 the bench filter shows only unallocated staff', async ({ page }) => {
    await login(page, 'manager')
    await page.goto('/resources?band=bench')
    const cells = page.locator('tbody tr td:nth-child(4)')
    await expect(cells.first()).toBeVisible()
    for (const text of await cells.allTextContents()) expect(text).toBe('0%')
  })
})
