// Pipeline stages, in order. Mirrors backend/app/engine/pipeline.py.
export const FLOW = ['applied', 'screened', 'interview', 'offer', 'hired']
export const STAGES = [...FLOW, 'rejected']

export const STAGE_LABELS = {
  applied: 'Applied',
  screened: 'Screened',
  interview: 'Interview',
  offer: 'Offer',
  hired: 'Hired',
  rejected: 'Rejected',
}

/** Label for the main action that moves an application to `stage`. */
export function moveLabel(stage) {
  return {
    screened: 'Mark as screened',
    interview: 'Move to interview',
    offer: 'Make an offer',
    hired: 'Mark as hired',
    rejected: 'Reject',
  }[stage] || `Reopen at ${STAGE_LABELS[stage]}`
}

/** Groups applications by stage, keeping the given order inside each column. */
export function groupByStage(apps) {
  const out = Object.fromEntries(STAGES.map((s) => [s, []]))
  for (const a of apps) (out[a.stage] || (out[a.stage] = [])).push(a)
  return out
}
