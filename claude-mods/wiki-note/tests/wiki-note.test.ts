import { test, expect, mock } from 'claude-code/testing'
import { USAGE, localDate, parseNote } from '../hooks/register'

const NOW = new Date(2026, 9, 8, 18, 0).getTime() // local 2026-10-08 18:00
const MIN = 60_000
const LOG = '---\ntype: log\n---\n\n## [2026-10-06] result | A\nx\n\n## [2026-10-07] decision | B\ny\n'

// Stand-ins for the engine: files in memory (paths reach hooks absolute, so match on the end),
// the status line and command registration.
function setup(on: any, files: Record<string, string>, mtimes: Record<string, number> = {}) {
  const clock = mock.clock(on, { now: NOW })
  const seen = { status: [] as (string | undefined)[], registered: [] as string[], files }
  const key = (p: string) => Object.keys(files).find(k => p === k || p.endsWith(`/${k}`))
  const isDir = (p: string) => Object.keys(files).some(k => k.startsWith(`${p.replace(/^.*?\/(?=[^/]+\/)/, '')}/`) || p.endsWith('/' + k.slice(0, k.lastIndexOf('/'))))
  on('fs.exists', (_$: any, e: any) => ({ value: key(e.path) !== undefined || isDir(e.path) }))
  on('fs.read', (_$: any, e: any) => ({ value: files[key(e.path)!] }))
  on('fs.write', (_$: any, e: any) => {
    files[key(e.path) ?? e.path] = e.text
    return { value: undefined }
  })
  on('fs.list', (_$: any, e: any) => ({
    value: Object.keys(files)
      .filter(k => e.path.endsWith('/' + k.slice(0, k.lastIndexOf('/'))))
      .map(k => ({ name: k.slice(k.lastIndexOf('/') + 1), kind: 'file', size: 1, mtimeMs: mtimes[k] ?? NOW, isLink: false })),
  }))
  on('ui.status', (_$: any, e: any) => {
    seen.status.push(e.text)
    return { value: undefined }
  })
  on('session.start', (_$: any, e: any) => ({ cwd: e.cwd }))
  on('command.register', (_$: any, e: any) => {
    seen.registered.push(e.name)
    return { value: { command: e.name } }
  })
  return { seen, clock }
}

const start = ($: any) => $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })

test('parseNote', async () => {
  expect(parseNote('decision: Use SQLite -- faster reports')).toEqual({ kind: 'decision', title: 'Use SQLite', details: 'faster reports' })
  expect(parseNote('Result:  Drift accepted')).toEqual({ kind: 'result', title: 'Drift accepted', details: '' })
  expect(parseNote('gossip: x')).toBeUndefined()
  expect(parseNote('no kind here')).toBeUndefined()
  expect(parseNote('plan:   ')).toBeUndefined()
})

test('localDate uses the local calendar day', async () => {
  expect(localDate(NOW)).toBe('2026-10-08')
  expect(localDate(new Date(2026, 0, 2, 0, 30).getTime())).toBe('2026-01-02')
})

test('/note appends a dated entry to the wiki log', async ($, on) => {
  const { seen } = setup(on, { 'notebooks/knowledge/log.md': LOG })
  const r = await $.command.run({ command: 'note', args: 'decision: Logs in SQLite -- benchmark in HANDOFF' })
  expect(r.text).toContain('## [2026-10-08] decision | Logs in SQLite')
  expect(seen.files['notebooks/knowledge/log.md']).toBe(
    `${LOG}\n## [2026-10-08] decision | Logs in SQLite\nbenchmark in HANDOFF\n`,
  )
})

test('/note follows wikiDir from .claude/handoff.json', async ($, on) => {
  const { seen } = setup(on, {
    '.claude/handoff.json': JSON.stringify({ wikiDir: 'docs/kb', sessionLog: 'docs/kb/s-*.md' }),
    'docs/kb/log.md': '## [2026-10-01] plan | X\n',
  })
  await $.command.run({ command: 'note', args: 'plan: Next' })
  expect(seen.files['docs/kb/log.md']).toContain('## [2026-10-08] plan | Next\nNoted with /note')
})

test('/note without a kind shows the usage and writes nothing', async ($, on) => {
  const { seen } = setup(on, { 'notebooks/knowledge/log.md': LOG })
  const r = await $.command.run({ command: 'note', args: 'just text' })
  expect(r.text).toBe(USAGE)
  expect(seen.files['notebooks/knowledge/log.md']).toBe(LOG)
})

test('/note in a project without a wiki says so', async ($, on) => {
  setup(on, {})
  const r = await $.command.run({ command: 'note', args: 'plan: X' })
  expect(r.text).toContain('no notebooks/knowledge/log.md')
})

test('session start registers /note and shows handoff age + wiki log', async ($, on) => {
  const { seen, clock } = setup(
    on,
    { 'notebooks/knowledge/log.md': LOG, 'notebooks/knowledge/session-log-2026-10-08.md': '## Status\n' },
    { 'notebooks/knowledge/session-log-2026-10-08.md': NOW - 12 * MIN },
  )
  await start($)
  await clock.settle()
  expect(seen.registered).toEqual(['note'])
  expect(seen.status.at(-1)).toBe('handoff 12m · wiki 2026-10-07 (2)')
  await clock.advance(60 * MIN) // the status line refreshes each minute
  expect(seen.status.at(-1)).toBe('handoff 72m stale · wiki 2026-10-07 (2)')
})

test('no wiki and no session log: status line cleared', async ($, on) => {
  const { seen, clock } = setup(on, {})
  await start($)
  await clock.settle()
  expect(seen.status.at(-1)).toBeUndefined()
})

test('status uses the last log by name, not the newest mtime', async ($, on) => {
  const { seen, clock } = setup(
    on,
    { 'notebooks/knowledge/session-log-2026-10-06.md': '', 'notebooks/knowledge/session-log-2026-10-08.md': '' },
    { 'notebooks/knowledge/session-log-2026-10-06.md': NOW - 1 * MIN, 'notebooks/knowledge/session-log-2026-10-08.md': NOW - 90 * MIN },
  )
  await start($)
  await clock.settle()
  expect(seen.status.at(-1)).toBe('handoff 90m stale')
})
