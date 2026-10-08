import type { Register } from 'claude-code'

// Where the session log lives comes from the project's `.claude/handoff.json` (shared with the kit's
// /handoff skill and SessionStart / SessionEnd hooks):
//   { "sessionLog": "docs/session-log-*.md", "staleMin": 30 }
// Without that file the defaults below apply. Projects without the log folder are not guarded.
export const CONFIG = '.claude/handoff.json'
export const DEFAULT_LOG = 'notebooks/knowledge/session-log-*.md'
export const DEFAULT_STALE_MIN = 30
export const CLEAR_ANYWAY = 'Clear anyway'
export const CANCEL = 'Cancel, run /handoff first'

// "dir/name-*.md" -> the folder and a regex for the file name (`*` and `?`, in the file name only).
export function splitGlob(glob: string): { dir: string; name: RegExp } {
  const i = glob.lastIndexOf('/')
  const dir = i < 0 ? '.' : glob.slice(0, i) || '/'
  const pat = glob.slice(i + 1)
  const re = pat.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.')
  return { dir, name: new RegExp(`^${re}$`) }
}

type Config = { sessionLog: string; staleMin: number }

async function readConfig($: any): Promise<Config> {
  const cfg: Config = { sessionLog: DEFAULT_LOG, staleMin: DEFAULT_STALE_MIN }
  if (!(await $.fs.exists(CONFIG))) return cfg
  const raw = JSON.parse(String(await $.fs.read(CONFIG)))
  if (typeof raw.sessionLog === 'string' && raw.sessionLog) cfg.sessionLog = raw.sessionLog
  if (typeof raw.staleMin === 'number' && raw.staleMin > 0) cfg.staleMin = raw.staleMin
  return cfg
}

export const register: Register = on => {
  on('command.run', { command: 'clear' }, async ($, e0, next) => {
    const e = { ...e0, args: e0.args ?? '' }
    // `/clear force` skips the check.
    if (e.args.trim() === 'force') return next({ ...e, args: '' })

    let ageMin: number
    let name: string
    let staleMin: number
    try {
      const cfg = await readConfig($)
      staleMin = cfg.staleMin
      const { dir, name: re } = splitGlob(cfg.sessionLog)
      if (!(await $.fs.exists(dir))) return next(e)
      const logs = (await $.fs.list(dir)).filter(f => re.test(f.name))
      const newest = [...logs].sort((a, b) => b.mtimeMs - a.mtimeMs)[0]
      if (!newest) return next(e)
      ageMin = Math.round(((await $.clock.now()) - newest.mtimeMs) / 60000)
      name = newest.name
    } catch {
      return next(e) // never block /clear because the check itself failed (a broken config included)
    }
    if (ageMin <= staleMin) return next(e)

    let answer: string
    try {
      answer = await $.ui.ask(
        `${name} was last updated ${ageMin} min ago. Clear without /handoff?`,
        { header: 'Handoff', options: [CANCEL, CLEAR_ANYWAY] },
      )
    } catch {
      answer = CANCEL // dialog dismissed
    }
    if (answer === CLEAR_ANYWAY) return next(e)
    return { text: 'clear-guard: /clear cancelled. Run /handoff, then /clear (or /clear force).' }
  }).catch(($, e, next) =>
    // A failing guard must not trap the person: let /clear run unless it already ran.
    next.called ? { text: 'clear-guard: hook failed after /clear ran.' } : next(e),
  )
}
