import { BoltIcon, ActivityIcon } from './icons'
import { useTreeStore } from '../state/treeStore'
import { useMemo } from 'react'

function connectionLabel(wsConnected: boolean, loading: boolean) {
  if (loading) return { text: 'Thinking…', cls: 'running' as const }
  if (wsConnected) return { text: 'Live', cls: 'ok' as const }
  return { text: 'Idle', cls: 'off' as const }
}

export function Header() {
  const { wsConnected, loading, activeTaskId, pendingTaskLabel, nodes } = useTreeStore()
  const conn = connectionLabel(wsConnected, loading)

  const progress = useMemo(() => {
    if (!nodes.length) return null
    const total = nodes.length
    const done = nodes.filter(n => n.status === 'completed').length
    const running = nodes.filter(n => ['executing', 'running', 'thinking', 'synthesizing', 'waiting_children'].includes(n.status)).length
    const failed = nodes.filter(n => n.status === 'failed').length
    return { total, done, running, failed }
  }, [nodes])

  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-mark"><BoltIcon size={16} /></div>
        <div>
          <div className="brand-name">Parallel <span>Mind</span> 2.0</div>
          <div className="brand-sub">Self-healing hierarchy</div>
        </div>
      </div>

      <div className="header-center">
        {progress && (
          <div className="header-progress" title={`${progress.done}/${progress.total} done`}>
            <ActivityIcon size={13} />
            <span><strong>{progress.done}</strong>/{progress.total} done</span>
            {progress.running > 0 && <span>· {progress.running} running</span>}
            {progress.failed > 0 && <span style={{ color: 'var(--error)' }}>· {progress.failed} failed</span>}
          </div>
        )}
      </div>

      <div className="header-right">
        {activeTaskId && (
          <span className="task-chip" title={pendingTaskLabel || activeTaskId}>
            {pendingTaskLabel || activeTaskId}
          </span>
        )}
        <span className="status-pill">
          <span className={`status-dot ${conn.cls}`} />
          {conn.text}
        </span>
      </div>
    </header>
  )
}
