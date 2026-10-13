import { useTreeStore } from '../state/treeStore'
import { AlertIcon, XIcon } from './icons'
import { Warning } from '../state/types'

interface WarningItem extends Warning {
  isCustom?: boolean
  isGeneric?: boolean
}

export function HealthBar() {
  const { warnings, dismissWarning, nodes } = useTreeStore()

  const total = nodes.length
  const failed = nodes.filter(n => n.status === 'failed').length
  const pct = total ? Math.round((failed / total) * 100) : 0
  const showFailure = pct >= 60 || warnings.some(w => w.kind === 'failure_threshold')

  const warningItems: WarningItem[] = [
    ...(showFailure ? [{ kind: 'failure' as const, message: `Heads up — ${pct || 60}% of agents hit a snag. Self-healing is on it. Work continues.` }] : []),
    ...warnings.map(w => ({ ...w, isCustom: true })),
    ...(total > 0 && failed > 0 && !showFailure ? [{ kind: 'generic' as const, message: `Self-healing active · ${failed} of ${total} agents retried with a new model.`, isGeneric: true }] : []),
  ]

  return (
    <div className="warning-stack">
      {warningItems.map((w, i) => (
        <div key={i} className={`warning-card ${w.kind === 'degraded' ? 'degraded' : w.kind === 'error' ? 'error' : w.kind === 'failure' ? 'failure' : 'generic'} animate-slide-down stagger-1`} style={{ animationDelay: `${i * 60}ms` }}>
          <AlertIcon size={13} />
          <span>{w.message}</span>
          {!w.isGeneric && <button className="warning-close pressable" onClick={() => dismissWarning(i)}><XIcon size={12} /></button>}
        </div>
      ))}
    </div>
  )
}
