import type { Register } from 'claude-code'

// Paths come from the project's `.claude/handoff.json` (shared with clear-guard, the kit hooks and skills):
//   { "sessionLog": "notebooks/knowledge/session-log-*.md", "staleMin": 30, "wikiDir": "notebooks/knowledge" }
// Projects with neither a wiki log.md nor a session log get no status line and /note says so.
export const CONFIG = '.claude/handoff.json'
export const KINDS = ['ingest', 'result', 'decision', 'lesson', 'plan']
const DEFAULT_LOG = 'notebooks/knowledge/session-log-*.md'
const REFRESH_MS = 60_000
export const USAGE = `Usage: /note <kind>: <title> [-- details]   kinds: ${KINDS.join(', ')}`

type Config = { sessionLog: string; staleMin: number; wikiDir: string }

export function splitGlob(glob: string): { dir: string; name: RegExp } {
  const i = glob.lastIndexOf('/')
  const dir = i < 0 ? '.' : glob.slice(0, i) || '/'
  const re = glob.slice(i + 1).replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.')
  return { dir, name: new RegExp(`^${re}$`) }
}

async function readConfig($: any): Promise<Config> {
  const cfg: Config = { sessionLog: DEFAULT_LOG, staleMin: 30, wikiDir: '' }
  try {
    if (await $.fs.exists(CONFIG)) {
      const raw = JSON.parse(String(await $.fs.read(CONFIG)))
      if (typeof raw.sessionLog === 'string' && raw.sessionLog) cfg.sessionLog = raw.sessionLog
      if (typeof raw.staleMin === 'number' && raw.staleMin > 0) cfg.staleMin = raw.staleMin
      if (typeof raw.wikiDir === 'string' && raw.wikiDir) cfg.wikiDir = raw.wikiDir
    }
  } catch {
    // a broken config falls back to the defaults
  }
  cfg.wikiDir = cfg.wikiDir || splitGlob(cfg.sessionLog).dir
  return cfg
}

// Local calendar date of `ms` (the log uses the person's day, not UTC).
export function localDate(ms: number): string {
  const d = new Date(ms)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

// "decision: Use X -- why" -> { kind, title, details }; undefined when the kind is missing or unknown.
export function parseNote(args: string): { kind: string; title: string; details: string } | undefined {
  const m = /^\s*([A-Za-z]+)\s*:\s*(.+)$/s.exec(args)
  if (!m || !KINDS.includes(m[1].toLowerCase())) return undefined
  const [title, ...rest] = m[2].split(/\s+--\s+/)
  if (!title.trim()) return undefined
  return { kind: m[1].toLowerCase(), title: title.trim(), details: rest.join(' -- ').trim() }
}

// "handoff 12m · wiki 2026-10-08 (37)"; "handoff 95m stale" past staleMin; undefined when there is nothing.
async function statusText($: any): Promise<string | undefined> {
  const cfg = await readConfig($)
  const parts: string[] = []
  const now = await $.clock.now()
  const { dir, name } = splitGlob(cfg.sessionLog)
  if (await $.fs.exists(dir)) {
    const logs = (await $.fs.list(dir)).filter((f: any) => name.test(f.name))
    // last in name order (dated names), not newest mtime
      const newest = [...logs].sort((a: any, b: any) => (a.name < b.name ? 1 : a.name > b.name ? -1 : 0))[0]
    if (newest) {
      const age = Math.round((now - newest.mtimeMs) / 60000)
      parts.push(`handoff ${age}m${age > cfg.staleMin ? ' stale' : ''}`)
    }
  }
  const log = `${cfg.wikiDir}/log.md`
  if (await $.fs.exists(log)) {
    const heads = String(await $.fs.read(log)).match(/^## \[\d{4}-\d{2}-\d{2}\]/gm) ?? []
    const last = heads.length ? heads[heads.length - 1].slice(4, 14) : 'empty'
    parts.push(`wiki ${last} (${heads.length})`)
  }
  return parts.length ? parts.join(' · ') : undefined
}

async function refresh($: any) {
  try {
    $.ui.status(await statusText($))
  } catch {
    $.ui.status(undefined) // never let the status line break the session
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'note',
      description: 'Append a dated entry to the wiki log.md (kinds: ingest, result, decision, lesson, plan)',
      argumentHint: '<kind>: <title> [-- details]',
    })
    void refresh($)
    $.clock.every(REFRESH_MS, () => refresh($))
    return next(e)
  })

  on('command.run', { command: 'note' }, async ($, e) => {
    const note = parseNote(e.args ?? '')
    if (!note) return { text: USAGE }
    const cfg = await readConfig($)
    const path = `${cfg.wikiDir}/log.md`
    if (!(await $.fs.exists(path))) {
      return { text: `wiki-note: no ${path}. Set wikiDir in ${CONFIG} or run ~/agent-kit/install-project.sh.` }
    }
    const text = String(await $.fs.read(path))
    const date = localDate(await $.clock.now())
    const head = `## [${date}] ${note.kind} | ${note.title}`
    const body = note.details || 'Noted with /note; add the page link and commit hash.'
    await $.fs.write(path, `${text}${text.endsWith('\n') ? '' : '\n'}\n${head}\n${body}\n`)
    void refresh($)
    return { text: `wiki-note: added to ${path}:\n${head}\nCommit it with the page it belongs to (wiki rule).` }
  })
}
