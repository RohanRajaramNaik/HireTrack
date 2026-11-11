// Screenshot the coverage and Playwright HTML reports for the report document.
//   node e2e/capture-reports.mjs
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { chromium } from 'playwright-core'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const out = path.join(root, 'docs', 'screenshots')
const browser = await chromium.launch({ channel: 'msedge' }).catch(() => chromium.launch({ channel: 'chrome' }))
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } })

const shots = [
  ['testing/coverage/backend/index.html', 'tests-backend-coverage.png'],
  ['testing/coverage/frontend/index.html', 'tests-frontend-coverage.png'],
  ['testing/e2e-report/index.html', 'tests-e2e-report.png'],
]
for (const [file, name] of shots) {
  await page.goto(pathToFileURL(path.join(root, file)).href)
  await page.waitForTimeout(1200)
  await page.screenshot({ path: path.join(out, name) })
  console.log('captured', name)
}
await browser.close()
