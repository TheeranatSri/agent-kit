import type { Register } from 'claude-code'

// Projects without this folder are not guarded: /clear runs as usual.
const LOG_DIR = 'notebooks/knowledge'
const LOG_NAME = /^session-log-.*\.md$/
const STALE_MIN = 30
export const CLEAR_ANYWAY = 'Clear anyway'
export const CANCEL = 'Cancel, run /handoff first'

export const register: Register = on => {
  on('command.run', { command: 'clear' }, async ($, e0, next) => {
    const e = { ...e0, args: e0.args ?? '' }
    // `/clear force` skips the check.
    if (e.args.trim() === 'force') return next({ ...e, args: '' })

    let ageMin: number
    let name: string
    try {
      if (!(await $.fs.exists(LOG_DIR))) return next(e)
      const logs = (await $.fs.list(LOG_DIR)).filter(f => LOG_NAME.test(f.name))
      const newest = [...logs].sort((a, b) => b.mtimeMs - a.mtimeMs)[0]
      if (!newest) return next(e)
      ageMin = Math.round(((await $.clock.now()) - newest.mtimeMs) / 60000)
      name = newest.name
    } catch {
      return next(e) // never block /clear because the check itself failed
    }
    if (ageMin <= STALE_MIN) return next(e)

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
