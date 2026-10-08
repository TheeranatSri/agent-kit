import { test, expect, mock } from 'claude-code/testing'
import { CANCEL, CLEAR_ANYWAY } from '../hooks/register'

const NOW = 1_800_000_000_000
const MIN = 60_000

// Stand-ins for the engine beneath the mod: the log folder, the dialog, and /clear itself.
function setup(on: any, opts: { exists?: boolean; logAgeMin?: number; answer?: string }) {
  mock.clock(on, { now: NOW })
  const seen = { cleared: 0, asked: 0 }
  on('fs.exists', () => ({ value: opts.exists ?? true }))
  on('fs.list', () => ({
    value: opts.logAgeMin === undefined
      ? []
      : [
          { name: 'session-log-2026-10-06.md', kind: 'file', size: 1, mtimeMs: NOW - 999 * MIN, isLink: false },
          { name: 'session-log-2026-10-08.md', kind: 'file', size: 1, mtimeMs: NOW - opts.logAgeMin * MIN, isLink: false },
          { name: 'lessons.md', kind: 'file', size: 1, mtimeMs: NOW, isLink: false },
        ],
  }))
  on('tool.call', { tool: 'AskUserQuestion' }, (_$: any, e: any) => {
    seen.asked++
    const q = e.questions[0].question
    return { result: { questions: e.questions, answers: { [q]: opts.answer ?? CANCEL } } }
  })
  on('command.run', { command: 'clear' }, () => {
    seen.cleared++
    return { text: 'cleared' }
  })
  return seen
}

test('fresh session log: clears without asking', async ($, on) => {
  const seen = setup(on, { logAgeMin: 5 })
  await $.command.run({ command: 'clear' })
  expect(seen).toEqual({ cleared: 1, asked: 0 })
})

test('stale log, user cancels: /clear does not run', async ($, on) => {
  const seen = setup(on, { logAgeMin: 90, answer: CANCEL })
  const r = await $.command.run({ command: 'clear' })
  expect(seen).toEqual({ cleared: 0, asked: 1 })
  expect(r.text).toContain('cancelled')
})

test('stale log, user confirms: clears', async ($, on) => {
  const seen = setup(on, { logAgeMin: 90, answer: CLEAR_ANYWAY })
  await $.command.run({ command: 'clear' })
  expect(seen).toEqual({ cleared: 1, asked: 1 })
})

test('/clear force skips the check', async ($, on) => {
  const seen = setup(on, { logAgeMin: 90 })
  await $.command.run({ command: 'clear', args: 'force' })
  expect(seen).toEqual({ cleared: 1, asked: 0 })
})

test('other projects (no log folder) are not guarded', async ($, on) => {
  const seen = setup(on, { exists: false })
  await $.command.run({ command: 'clear' })
  expect(seen).toEqual({ cleared: 1, asked: 0 })
})
