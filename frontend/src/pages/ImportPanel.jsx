import { Download, FileSpreadsheet } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../apiClient'
import { SlideOver } from '../components/Overlay'
import { useToast } from '../components/Toast'
import { Spinner } from '../components/ui'
import { bytes, plural } from '../lib/format'

const FIELD_NAMES = {
  full_name: 'Full name',
  email: 'Email',
  phone: 'Phone',
  location: 'Location',
  years_experience: 'Years',
  education: 'Education',
  previous_titles: 'Previous titles',
  skills: 'Skills',
  resume_summary: 'Resume summary',
}

/** Bulk import of candidates from a .csv or .xlsx file, with a per-row error report. */
export default function ImportPanel({ open, onClose, onImported }) {
  const toast = useToast()
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (open) {
      setFile(null)
      setResult(null)
      setError(null)
    }
  }, [open])

  const run = async () => {
    if (!file) {
      setError('Choose a .csv or .xlsx file first')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const r = await api.importCandidates(file)
      setResult(r)
      if (r.created) {
        toast.success(`${plural(r.created, 'candidate')} imported`)
        onImported?.()
      }
    } catch (err) {
      setError(err.detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <SlideOver
      open={open}
      onClose={onClose}
      title="Import candidates"
      subtitle="CSV or Excel (.xlsx), one candidate per row"
      footer={
        <>
          <button type="button" className="btn-primary" onClick={run} disabled={busy || !file}>
            {busy && <Spinner />} Import file
          </button>
          <button type="button" className="btn-ghost" onClick={onClose}>
            {result ? 'Done' : 'Cancel'}
          </button>
        </>
      }
    >
      <div className="space-y-5">
        <ol className="list-decimal space-y-1.5 pl-5 text-base text-muted">
          <li>
            Download the template. It lists the columns:{' '}
            <span className="text-ink">full_name, years_experience, education, skills, resume_summary</span> are required;
            email, phone, location and previous_titles are optional.
          </li>
          <li>Separate skills with semicolons. Education can be a level name (for example Diploma) or 1 to 7.</li>
          <li>Rows are checked with the same rules as the Add Candidate form. Rows with an email already in the system are skipped.</li>
        </ol>
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={() => api.importTemplate().catch((e) => toast.error('Download failed', e.detail))}
        >
          <Download size={14} aria-hidden /> Download template
        </button>

        <div>
          <label className="label" htmlFor="import-file">
            File
          </label>
          <button
            type="button"
            className={`flex w-full items-center gap-3 rounded-lg border border-dashed px-4 py-4 text-left hover:bg-subtle ${
              error ? 'border-danger' : 'border-line-strong'
            }`}
            onClick={() => inputRef.current?.click()}
          >
            <FileSpreadsheet size={20} className="shrink-0 text-muted" aria-hidden />
            <span className="min-w-0">
              <span className="block truncate text-base font-medium text-ink">{file ? file.name : 'Choose a file'}</span>
              <span className="block text-sm text-faint">{file ? bytes(file.size) : '.csv or .xlsx, up to 5 MB'}</span>
            </span>
          </button>
          <input
            id="import-file"
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx"
            className="sr-only"
            onChange={(e) => {
              setFile(e.target.files?.[0] || null)
              setResult(null)
              setError(null)
            }}
          />
          {error && (
            <p role="alert" className="mt-1.5 text-sm text-danger">
              {error}
            </p>
          )}
        </div>

        {result && (
          <section aria-live="polite" className="rounded-lg border border-line">
            <div className="grid grid-cols-3 divide-x divide-line border-b border-line text-center">
              {[
                ['Imported', result.created],
                ['Skipped (already exist)', result.skipped],
                ['Rows with errors', result.errors.length],
              ].map(([label, n]) => (
                <div key={label} className="px-3 py-3">
                  <p className="tnum text-xl font-semibold text-ink">{n}</p>
                  <p className="text-xs text-muted">{label}</p>
                </div>
              ))}
            </div>
            {result.errors.length > 0 && (
              <div className="max-h-72 overflow-y-auto">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-canvas">
                    <tr>
                      <th className="th px-3 py-2">Row</th>
                      <th className="th px-3 py-2">Column</th>
                      <th className="th px-3 py-2">Problem</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {result.errors.map((e) => (
                      <tr key={`${e.row}-${e.field}`}>
                        <td className="tnum px-3 py-2 text-ink">{e.row}</td>
                        <td className="px-3 py-2 text-muted">{FIELD_NAMES[e.field] || e.field || '–'}</td>
                        <td className="px-3 py-2 text-ink">{e.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="border-t border-line px-3 py-2 text-xs text-faint">
                  Fix these rows in the file and import it again. Rows already imported will be skipped.
                </p>
              </div>
            )}
          </section>
        )}
      </div>
    </SlideOver>
  )
}
