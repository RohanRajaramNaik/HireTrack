// Starts an isolated HireTrack server for the Playwright suite.
//  1. builds the frontend (so the tests always run against the current code)
//  2. seeds a separate database in ../e2e-data (never touches data/)
//  3. runs uvicorn on 127.0.0.1:8010
// Playwright starts this through `webServer` in playwright.config.js.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, rmSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const frontend = path.resolve(here, '..')
const root = path.resolve(frontend, '..')
const dataRoot = path.join(root, 'e2e-data')
const port = process.env.HT_E2E_PORT || '8010'

const py = [path.join(root, '.venv', 'Scripts', 'python.exe'), path.join(root, '.venv', 'bin', 'python')].find(existsSync)
if (!py) {
  console.error('Python virtual environment not found. Follow INSTALLATION_GUIDE.md first.')
  process.exit(1)
}

const env = {
  ...process.env,
  HIRETRACK_DATA_DIR: path.join(dataRoot, 'data'),
  HIRETRACK_BACKUP_DIR: path.join(dataRoot, 'backups'),
  HIRETRACK_LOG_DIR: path.join(dataRoot, 'logs'),
  HF_HUB_OFFLINE: '1',
  PYTHONUTF8: '1',
}

function run(cmd, args, opts) {
  const r = spawnSync(cmd, args, { stdio: 'inherit', shell: process.platform === 'win32' && cmd === 'npm', ...opts })
  if (r.status !== 0) process.exit(r.status || 1)
}

if (process.env.HT_E2E_SKIP_BUILD !== '1') run('npm', ['run', 'build'], { cwd: frontend })

// Fresh database every run so the suite is repeatable. Keep the embedding cache
// between runs (it only holds vectors keyed by a hash of the CV text).
const cache = path.join(dataRoot, 'data', 'embedding_cache.npz')
rmSync(path.join(dataRoot, 'backups'), { recursive: true, force: true })
for (const f of ['hiretrack.db', 'hiretrack.db-journal']) rmSync(path.join(dataRoot, 'data', f), { force: true })
mkdirSync(path.join(dataRoot, 'data'), { recursive: true })
console.log(existsSync(cache) ? 'Reusing the e2e embedding cache' : 'First e2e run: the CVs will be encoded once')

run(py, [path.join(root, 'seed', 'seed_database.py')], { cwd: root, env })

const server = spawn(py, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', port], {
  cwd: path.join(root, 'backend'),
  env, // same start-up as the real app: daily backup + model warm-up in the background
  stdio: 'inherit',
})
const stop = () => server.kill()
process.on('SIGINT', stop)
process.on('SIGTERM', stop)
process.on('exit', stop)
server.on('exit', (code) => process.exit(code ?? 0))
