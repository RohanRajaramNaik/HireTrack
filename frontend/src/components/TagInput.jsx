import { X } from 'lucide-react'
import { useState } from 'react'
import { normaliseSkill } from '../lib/validation'

/**
 * Skill chips. Enter or comma adds a chip, Backspace on an empty field removes
 * the last one, pasting "a, b, c" adds several. Duplicates (after alias
 * normalisation, so "JS" and "JavaScript" count as one) are ignored.
 */
export default function TagInput({ id, value, onChange, placeholder = 'Type a skill and press Enter', invalid, describedBy, tone = 'default', label }) {
  const [draft, setDraft] = useState('')
  const [note, setNote] = useState('')

  const add = (raw) => {
    const parts = raw
      .split(/[,;\n]/)
      .map((s) => s.trim().replace(/\s+/g, ' '))
      .filter(Boolean)
    if (!parts.length) return
    const seen = new Set(value.map(normaliseSkill))
    const next = [...value]
    const dupes = []
    for (const p of parts) {
      const key = normaliseSkill(p)
      if (seen.has(key)) dupes.push(p)
      else if (p.length <= 60) {
        seen.add(key)
        next.push(p)
      }
    }
    setNote(dupes.length ? `${dupes.join(', ')} already added` : '')
    if (next.length !== value.length) onChange(next)
    setDraft('')
  }

  const remove = (i) => onChange(value.filter((_, j) => j !== i))

  const onKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      add(draft)
    } else if (e.key === 'Backspace' && !draft && value.length) {
      remove(value.length - 1)
    }
  }

  const chipClass = tone === 'required' ? 'chip-match' : 'chip'

  return (
    <div>
      <div
        className={`flex min-h-9 flex-wrap items-center gap-1.5 rounded border bg-surface px-1.5 py-1 transition-colors focus-within:ring-2 ${
          invalid ? 'border-danger focus-within:ring-danger/20' : 'border-line-strong hover:border-faint focus-within:border-accent focus-within:ring-accent/20'
        }`}
        onClick={(e) => e.currentTarget.querySelector('input')?.focus()}
      >
        <ul className="contents" aria-label={label ? `${label} added` : 'Added skills'}>
          {value.map((tag, i) => (
            <li key={`${tag}-${i}`} className={`${chipClass} pr-1`}>
              <span>{tag}</span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  remove(i)
                }}
                className="rounded p-0.5 text-faint hover:bg-line hover:text-ink"
                aria-label={`Remove ${tag}`}
              >
                <X size={12} />
              </button>
            </li>
          ))}
        </ul>
        <input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => draft.trim() && add(draft)}
          onPaste={(e) => {
            const text = e.clipboardData.getData('text')
            if (/[,;\n]/.test(text)) {
              e.preventDefault()
              add(text)
            }
          }}
          placeholder={value.length ? '' : placeholder}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          className="h-7 min-w-[8rem] flex-1 bg-transparent px-1.5 text-base text-ink placeholder:text-faint focus:outline-none"
        />
      </div>
      {note && <p className="hint mt-1">{note}</p>}
    </div>
  )
}
