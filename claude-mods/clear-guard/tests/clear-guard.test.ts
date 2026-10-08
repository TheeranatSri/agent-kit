import { test, expect, mock } from 'claude-code/testing'
import { CANCEL, CLEAR_ANYWAY, splitGlob } from '../hooks/register'

const NOW = 1_800_000_000_000
const MIN = 60_000

// Stand-ins for the engine beneath the mod: the project files, the dialog, and /clear itself.
// `config` is the text of .claude/handoff.json (absent when undefined); `logDir` is where the logs are.
function setup(
  on: any,
  opts: { exists?: boolean; logAgeMin?: number; oldLogAgeMin?: number; answer?: string; config?: string; logDir?: string; logPrefix?: string },
) {
  mock.clock(on, { now: NOW })
  const seen = { cleared: 0, asked: 0, listed: [] as string[] }
  const logDir = opts.logDir ?? 'notebooks/knowledge'
  const prefix = opts.logPrefix ?? 'session-log-'
  // The engine hands hooks absolute paths, so match on the end of the path.
  const is = (path: string, rel: string) => path === rel || path.endsWith(`/${rel}`)
  on('fs.exists', (_$: any, e: any) => ({
    value: is(e.path, '.claude/handoff.json') ? opts.config !== undefined : is(e.path, logDir) && (opts.exists ?? true),
  }))
  on('fs.read', (_$: any, e: any) => ({ value: is(e.path, '.claude/handoff.json') ? opts.config : '' }))
  on('fs.list', (_$: any, e: any) => {
    seen.listed.push(e.path)
    return {
      value: opts.logAgeMin === undefined || !is(e.path, logDir)
        ? []
        : [
            { name: `${prefix}2026-10-06.md`, kind: 'file', size: 1, mtimeMs: NOW - (opts.oldLogAgeMin ?? 999) * MIN, isLink: false },
            { name: `${prefix}2026-10-08.md`, kind: 'file', size: 1, mtimeMs: NOW - opts.logAgeMin * MIN, isLink: false },
            { name: 'lessons.md', kind: 'file', size: 1, mtimeMs: NOW, isLink: false },
          ],
    }
  })
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
  expect([seen.cleared, seen.asked]).toEqual([1, 0])
})

test('stale log, user cancels: /clear does not run', async ($, on) => {
  const seen = setup(on, { logAgeMin: 90, answer: CANCEL })
  const r = await $.command.run({ command: 'clear' })
  expect([seen.cleared, seen.asked]).toEqual([0, 1])
  expect(r.text).toContain('cancelled')
})

test('stale log, user confirms: clears', async ($, on) => {
  const seen = setup(on, { logAgeMin: 90, answer: CLEAR_ANYWAY })
  await $.command.run({ command: 'clear' })
  expect([seen.cleared, seen.asked]).toEqual([1, 1])
})

test('/clear force skips the check', async ($, on) => {
  const seen = setup(on, { logAgeMin: 90 })
  await $.command.run({ command: 'clear', args: 'force' })
  expect([seen.cleared, seen.asked]).toEqual([1, 0])
})

test('other projects (no log folder) are not guarded', async ($, on) => {
  const seen = setup(on, { exists: false })
  await $.command.run({ command: 'clear' })
  expect([seen.cleared, seen.asked]).toEqual([1, 0])
})

test('config: log in another folder with another name is guarded', async ($, on) => {
  const config = JSON.stringify({ sessionLog: 'docs/handoff-*.md' })
  const seen = setup(on, { config, logDir: 'docs', logPrefix: 'handoff-', logAgeMin: 90 })
  await $.command.run({ command: 'clear' })
  expect([seen.cleared, seen.asked]).toEqual([0, 1])
  expect(seen.listed.length).toBe(1)
  expect(seen.listed[0].endsWith('/docs')).toBe(true)
})

test('config: staleMin raises the limit', async ($, on) => {
  const seen = setup(on, { config: JSON.stringify({ staleMin: 120 }), logAgeMin: 90 })
  await $.command.run({ command: 'clear' })
  expect([seen.cleared, seen.asked]).toEqual([1, 0])
})

test('broken config never blocks /clear', async ($, on) => {
  const seen = setup(on, { config: '{ not json', logAgeMin: 90 })
  await $.command.run({ command: 'clear' })
  expect([seen.cleared, seen.asked]).toEqual([1, 0])
})

test('splitGlob', async () => {
  const g = splitGlob('docs/session-log-*.md')
  expect(g.dir).toBe('docs')
  expect(g.name.test('session-log-2026-10-08.md')).toBe(true)
  expect(g.name.test('session-logX.md')).toBe(false)
  expect(g.name.test('session-log-1.mdx')).toBe(false)
  expect(splitGlob('log-?.md').dir).toBe('.')
})

test('an older log edited later does not hide a stale current log', async ($, on) => {
  const seen = setup(on, { logAgeMin: 90, oldLogAgeMin: 1 })
  await $.command.run({ command: 'clear' })
  expect([seen.cleared, seen.asked]).toEqual([0, 1])
})
