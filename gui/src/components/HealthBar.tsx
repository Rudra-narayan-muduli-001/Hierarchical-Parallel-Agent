import { useTreeStore } from '../state/treeStore'
import { AlertIcon, XIcon } from './icons'

export function HealthBar() {
  const { warnings, dismissWarning, nodes } = useTreeStore()

  const total = nodes.length
  const failed = nodes.filter(n => n.status === 'failed').length
  const pct = total ? Math.round((failed / total) * 100) : 0
  const showFailure = pct >= 60 || warnings.some(w => w.kind === 'failure_threshold')

  return (
    <div className="warning-stack">
      {showFailure && (
        <div className="warning-card failure">
          <AlertIcon size={13} />
          <span>Heads up — {pct || 60}% of agents hit a snag. Self-healing is on it. Work continues.</span>
        </div>
      )}
      {warnings.map((w, i) => (
        <div key={i} className={`warning-card ${w.kind === 'degraded' ? 'degraded' : w.kind === 'error' ? 'error' : 'generic'}`}>
          <AlertIcon size={13} />
          <span>{w.message}</span>
          <button className="warning-close" onClick={() => dismissWarning(i)}><XIcon size={12} /></button>
        </div>
      ))}
      {total > 0 && failed > 0 && !showFailure && (
        <div className="warning-card generic" style={{ fontSize: 11 }}>
          Self-healing active · {failed} of {total} agents retried with a new model.
        </div>
      )}
    </div>
  )
}
