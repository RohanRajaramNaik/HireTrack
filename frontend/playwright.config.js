// Playwright end-to-end suite (system testing).
//   npm run test:e2e
// Uses the installed Microsoft Edge (or Chrome with HT_BROWSER=chrome), so no
// browser download is needed. A separate server and database are started on
// port 8010 (see e2e/start-e2e-server.mjs); your own data is never touched.
import { defineConfig } from '@playwright/test'

const port = process.env.HT_E2E_PORT || '8010'
const baseURL = process.env.HT_BASE || `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: './e2e/tests',
  fullyParallel: false,
  workers: 1, // one shared database: run the journeys in order
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: '../testing/e2e-report', open: 'never' }],
    ['junit', { outputFile: '../testing/results/e2e-junit.xml' }],
  ],
  use: {
    baseURL,
    channel: process.env.HT_BROWSER === 'chrome' ? 'chrome' : 'msedge',
    viewport: { width: 1366, height: 768 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    acceptDownloads: true,
  },
  webServer: process.env.HT_BASE
    ? undefined
    : {
        command: 'node e2e/start-e2e-server.mjs',
        url: `${baseURL}/api/health`,
        timeout: 240_000,
        reuseExistingServer: false,
        stdout: 'pipe',
      },
})
