import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import MetricBar from '../components/MetricBar'
import WeightSliders from '../components/WeightSliders'
import TagInput from '../components/TagInput'

describe('MetricBar', () => {
  it('shows the label and the number (not colour alone)', () => {
    render(<MetricBar label="Skills" value={83.3} animated={false} />)
    const meter = screen.getByRole('meter', { name: 'Skills' })
    expect(meter).toHaveAttribute('aria-valuenow', '83.3')
    expect(meter).toHaveAttribute('aria-valuetext', 'Skills 83.3 out of 100')
    expect(screen.getByText('83.3')).toBeInTheDocument()
  })

  it('clamps out-of-range values to 0-100', () => {
    render(<MetricBar label="Experience" value={140} animated={false} />)
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '100')
  })

  it('fills the bar in proportion to the value', () => {
    render(<MetricBar label="Education" value={25} animated={false} />)
    expect(screen.getByTestId('metric-fill').style.transform).toContain('scaleX(0.25)')
  })
})

function Harness({ mode, initial, onChangeSpy }) {
  const [w, setW] = useState(initial)
  return (
    <WeightSliders
      mode={mode}
      weights={w}
      onChange={(next) => {
        onChangeSpy?.(next)
        setW(next)
      }}
      onReset={() => setW({ skills: 40, experience: 25, education: 15, semantic: 20 })}
    />
  )
}

describe('WeightSliders', () => {
  const defaults = { skills: 40, experience: 25, education: 15, semantic: 20 }

  it('shows a live total of 100% for defaults', () => {
    render(<Harness mode="manual" initial={defaults} />)
    expect(screen.getByTestId('weight-total')).toHaveTextContent('Total 100%')
  })

  it('manual mode: typing a weight changes the total and says what is left', () => {
    render(<Harness mode="manual" initial={defaults} />)
    fireEvent.change(screen.getByLabelText('Meaning match weight, percent'), { target: { value: '15' } })
    expect(screen.getByTestId('weight-total')).toHaveTextContent('Total 95%')
    expect(screen.getByTestId('weight-total')).toHaveTextContent('5% still to assign')
  })

  it('manual mode: reports when over 100', () => {
    render(<Harness mode="manual" initial={defaults} />)
    fireEvent.change(screen.getByLabelText('Skills weight, percent'), { target: { value: '50' } })
    expect(screen.getByTestId('weight-total')).toHaveTextContent('10% over')
  })

  it('balanced mode: dragging one slider keeps the total at 100', () => {
    const spy = vi.fn()
    render(<Harness mode="balanced" initial={defaults} onChangeSpy={spy} />)
    fireEvent.change(document.getElementById('w-semantic-range'), { target: { value: '60' } })
    const next = spy.mock.calls.at(-1)[0]
    expect(next.semantic).toBe(60)
    expect(next.skills + next.experience + next.education + next.semantic).toBe(100)
    expect(screen.getByTestId('weight-total')).toHaveTextContent('Total 100%')
  })

  it('reset restores the defaults', () => {
    render(<Harness mode="manual" initial={{ skills: 10, experience: 10, education: 10, semantic: 10 }} />)
    fireEvent.click(screen.getByRole('button', { name: /reset to defaults/i }))
    expect(screen.getByTestId('weight-total')).toHaveTextContent('Total 100%')
  })
})

describe('TagInput', () => {
  function TagHarness() {
    const [v, setV] = useState([])
    return <TagInput id="t" value={v} onChange={setV} label="Skills" />
  }

  it('adds a chip on Enter and ignores alias duplicates', () => {
    render(<TagHarness />)
    const input = document.getElementById('t')
    fireEvent.change(input, { target: { value: 'JS' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    fireEvent.change(input, { target: { value: 'JavaScript' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
    expect(screen.getByText('JavaScript already added')).toBeInTheDocument()
  })

  it('removes the last chip with Backspace on an empty field', () => {
    render(<TagHarness />)
    const input = document.getElementById('t')
    fireEvent.change(input, { target: { value: 'Python, SQL' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    fireEvent.keyDown(input, { key: 'Backspace' })
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
  })
})
