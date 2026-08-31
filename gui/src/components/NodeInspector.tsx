import { useTreeStore } from '../state/treeStore'
import { NetworkIcon, XIcon } from './icons'
import { MarkdownViewer } from './MarkdownViewer'

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="stat"><div className="stat-label">{label}</div><div className="stat-value" title={value}>{value}</div></div>
}

export function NodeInspector() {
  const { selectedNode, nodeOutputs, selectNode, nodes } = useTreeStore()
  const node = selectedNode

  if (!node) {
    const active = nodes.filter(n => ['executing', 'running', 'thinking', 'synthesizing', 'waiting_children'].includes(n.status))
    return (
      <div className="detail detail-empty">
        <div className="detail-empty-inner">
          <NetworkIcon size={26} />
          <div>
            <h4 style={{ marginBottom: 4, color: 'var(--text)' }}>Inspector</h4>
            <p>Pick a node in the hierarchy to see its thoughts, output and live state.</p>
          </div>
        </div>
        {active.length > 0 && (
          <div style={{ width: '100%', marginTop: 8 }}>
            <div className="panel-title" style={{ paddingLeft: 0 }}>Currently running</div>
            <div className="stream-list">
              {active.slice(0, 6).map(n => (
                <button key={n.id} className="stream-row" onClick={() => selectNode(n.id)}>
                  <span className={`role-chip role-${n.role}`}>{n.role}</span>
                  <span className="stream-id">{n.id.slice(0, 14)}</span>
                  <span className="stream-state">{n.status}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  const live = nodeOutputs[node.id]
  const output = live ?? node.output ?? ''
  const rolePlain = node.role === 'boss' ? 'Director' : node.role === 'manager' ? 'Team Lead' : node.role === 'supervisor' ? 'Coordinator' : 'Worker'

  return (
    <div className="detail">
      <div className="detail-head">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'flex-start' }}>
          <div className="detail-badges">
            <span className={`role-chip role-${node.role}`} title={rolePlain}>{node.role}</span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{rolePlain}</span>
            <span className="task-chip" style={{ fontSize: 10 }}>{node.tier || '—'}</span>
            {node.reused && <span className="task-chip" style={{ background: 'rgba(245,158,11,0.15)', color: 'var(--warning)', borderColor: 'rgba(245,158,11,0.25)' }}>♻ reused</span>}
          </div>
          <button className="icon-btn-sm" onClick={() => selectNode(null)} title="Close"><XIcon size={13} /></button>
        </div>
        <div className="detail-id" title={node.id}>{node.id}</div>
      </div>

      <div className="stat-grid">
        <Stat label="Status" value={node.status} />
        <Stat label="Model" value={node.model_id || '—'} />
        <Stat label="Retries" value={String(node.retries ?? 0)} />
        <Stat label="Parent" value={node.parent_id || 'root'} />
        <Stat label="Category" value={node.category || '—'} />
        <Stat label="Reused" value={node.reused ? 'yes — pool fallback' : 'no'} />
      </div>

      <div>
        <div className="panel-title">Output</div>
        {output ? <div className="assistant-card"><div className="assistant-card-body"><MarkdownViewer content={output} /></div></div> : <p className="no-data">No output yet — this agent is still working.</p>}
      </div>

      <div>
        <div className="panel-title">Thought stream</div>
        {node.thought_stream && node.thought_stream.length > 0 ? (
          <div className="thought-list">
            {node.thought_stream.map((t, i) => (
              <div key={i} className="thought-row">
                <span className="thought-time">{new Date(t.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                <span className="thought-text">{t.text}</span>
              </div>
            ))}
          </div>
        ) : <p className="no-data">No thoughts recorded.</p>}
      </div>

      {node.error && (
        <div>
          <div className="panel-title" style={{ color: 'var(--error)' }}>Error</div>
          <pre className="error-block">{node.error}</pre>
        </div>
      )}

      {node.replaced_history && node.replaced_history.length > 0 && (
        <div>
          <div className="panel-title">Replace history</div>
          <div className="thought-list">
            {node.replaced_history.map((r, i) => (
              <div key={i} className="thought-row">
                <span className="thought-time">{new Date(r.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                <span className="thought-text">{r.from_model} → {r.to_model} ({r.reason})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
