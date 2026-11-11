import { expect, test } from '@playwright/test'
import { login, toast, uid } from './helpers'

test.describe('Candidate management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, 'recruiter')
    await page.getByRole('navigation', { name: 'Main' }).first().getByRole('link', { name: 'Candidates' }).click()
    await expect(page.getByText('600 candidates in the database')).toBeVisible()
  })

  test('TC-05 invalid candidate data is refused with messages under each field', async ({ page }) => {
    await page.getByRole('button', { name: 'Add candidate' }).first().click()
    const panel = page.getByRole('dialog')
    await panel.getByLabel('Years of experience').fill('-2')
    await panel.getByRole('button', { name: 'Add candidate' }).click()
    await expect(panel.getByText('Full name is required')).toBeVisible()
    await expect(panel.getByText('Years of experience cannot be less than 0')).toBeVisible()
    await expect(panel.getByText('Choose an education level')).toBeVisible()
    await expect(panel.getByText('Add at least one skill')).toBeVisible()
    await expect(page.getByText('600 candidates in the database')).toBeVisible()
  })

  test('TC-06 add, find, edit and delete a candidate', async ({ page }) => {
    const name = `Zinhle Test ${uid()}`
    await page.getByRole('button', { name: 'Add candidate' }).first().click()
    const panel = page.getByRole('dialog')
    await panel.getByLabel('Full name').fill(name)
    await panel.getByLabel('Location').fill('Durban')
    await panel.getByLabel('Years of experience').fill('4')
    await panel.getByLabel('Highest education').selectOption({ label: "Bachelor's Degree" })
    const skills = panel.getByLabel('Skills', { exact: true })
    await skills.first().fill('Python')
    await skills.first().press('Enter')
    await skills.first().fill('K8s')
    await skills.first().press('Enter')
    await panel
      .getByLabel('Resume summary')
      .fill('Platform engineer who runs Kubernetes clusters and writes Python automation for a retailer.')
    await panel.getByRole('button', { name: 'Add candidate' }).click()
    await toast(page, 'Candidate added')
    await expect(page.getByText('601 candidates in the database')).toBeVisible()

    await page.getByLabel('Search candidates').fill(name)
    await expect(page.getByText('1 of 601 shown')).toBeVisible()
    await page.getByRole('button', { name: `Edit ${name}` }).click()
    await page.getByRole('dialog').getByLabel('Years of experience').fill('5')
    await page.getByRole('dialog').getByRole('button', { name: 'Save changes' }).click()
    await toast(page, 'Candidate updated')
    await expect(page.getByText('5 yrs')).toBeVisible()

    await page.getByRole('button', { name: `Edit ${name}` }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Delete candidate' }).click()
    await toast(page, 'Candidate deleted')
    await expect(page.getByText('600 candidates in the database')).toBeVisible()
  })

  test('TC-07 a CV file fills in the summary and skills', async ({ page }) => {
    await page.getByRole('button', { name: 'Add candidate' }).first().click()
    const panel = page.getByRole('dialog')
    await panel.getByTestId('cv-file').setInputFiles({
      name: 'cv.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(
        'Mpho Radebe\nmpho.radebe@example.com  082 555 7788\nData engineer building Airflow pipelines in Python and SQL on AWS.',
      ),
    })
    await expect(panel.getByText(/Read cv.txt/)).toBeVisible()
    await expect(panel.getByLabel('Full name')).toHaveValue('Mpho Radebe')
    await expect(panel.getByLabel('Resume summary')).toHaveValue(/Airflow pipelines/)
    await expect(panel.getByText('Airflow', { exact: true })).toBeVisible()
  })

  test('TC-08 bulk import saves valid rows and reports bad rows', async ({ page }) => {
    const id = uid()
    const csv = [
      'full_name,email,location,years_experience,education,skills,resume_summary',
      `Import One ${id},one.${id}@example.com,Cape Town,3,Diploma,SQL; Power BI,Builds Power BI dashboards and SQL reports for a retailer.`,
      `Import Two ${id},two.${id}@example.com,Pretoria,6,Honours,Python; Spark,Data engineer running Spark jobs on a cloud data platform.`,
      `Bad Row ${id},bad.${id}@example.com,Durban,-1,Diploma,SQL,Valid summary text that is long enough to pass.`,
    ].join('\n')
    await page.getByRole('button', { name: 'Import CSV or Excel' }).click()
    const panel = page.getByRole('dialog')
    await panel.locator('#import-file').setInputFiles({ name: 'candidates.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
    await panel.getByRole('button', { name: 'Import file' }).click()
    await expect(panel.getByText('Rows with errors')).toBeVisible()
    await expect(panel.getByRole('cell', { name: 'Cannot be less than 0' })).toBeVisible()
    await expect(panel.getByRole('cell', { name: '4', exact: true })).toBeVisible()
    await panel.getByRole('button', { name: 'Done' }).click()
    await expect(page.getByText('602 candidates in the database')).toBeVisible()
  })
})
