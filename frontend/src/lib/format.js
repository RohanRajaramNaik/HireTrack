const asDate = (iso) => new Date(/Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z')

export function timeAgo(iso) {
  if (!iso) return 'Never'
  const s = Math.round((Date.now() - asDate(iso).getTime()) / 1000)
  if (s < 45) return 'Just now'
  const m = Math.round(s / 60)
  if (m < 60) return `${m} min ago`
  const h = Math.round(m / 60)
  if (h < 24) return `${h} hr ago`
  const days = Math.round(h / 24)
  if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`
  return asDate(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function dateTime(iso) {
  if (!iso) return ''
  return asDate(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function years(n) {
  const v = Number(n)
  const s = Number.isInteger(v) ? String(v) : v.toFixed(1)
  return `${s} yr${v === 1 ? '' : 's'}`
}

export function plural(n, word, pluralWord) {
  return `${Number(n).toLocaleString()} ${n === 1 ? word : pluralWord || word + 's'}`
}

export function bytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

const SPECIAL = {
  aws: 'AWS', sql: 'SQL', gcp: 'GCP', dbt: 'dbt', 'ci/cd': 'CI/CD', etl: 'ETL', bpmn: 'BPMN',
  'rest apis': 'REST APIs', 'node.js': 'Node.js', postgresql: 'PostgreSQL', javascript: 'JavaScript',
  typescript: 'TypeScript', 'power bi': 'Power BI', siem: 'SIEM', itil: 'ITIL', uml: 'UML', iam: 'IAM',
  'sql server': 'SQL Server', 'c#': 'C#', '.net': '.NET', html: 'HTML', css: 'CSS', php: 'PHP', s3: 'S3',
  'iso 27001': 'ISO 27001', dax: 'DAX', ssis: 'SSIS', mongodb: 'MongoDB', 'scikit-learn': 'scikit-learn',
  'machine learning': 'Machine Learning', 'github actions': 'GitHub Actions', tsql: 'T-SQL',
}

/** Display canonical (lowercase) skill names nicely, e.g. "postgresql" -> "PostgreSQL". */
export function skillLabel(s) {
  if (SPECIAL[s]) return SPECIAL[s]
  return s.replace(/(^|[\s-])([a-z])/g, (_, sp, c) => sp + c.toUpperCase())
}
