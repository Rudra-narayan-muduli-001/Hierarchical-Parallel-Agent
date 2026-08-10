import { useTreeStore } from '../state/treeStore';
import { Node } from '../state/types';
import { MarkdownViewer } from './MarkdownViewer';
import { CloseIcon, NetworkIcon } from './icons';

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value ellipsis" title={value}>{value}</span>
    </div>
  );
}

export function NodeDetailPanel() {
  const { selectedNode, nodeOutputs, selectNode, nodes } = useTreeStore();
  const node = selectedNode as Node | null;

  if (!node) {
    const active = nodes.filter(n => n.status === 'executing' || n.status === 'running');
    return (
      <div className="detail-panel detail-panel-empty">
        <div className="detail-empty-inner">
          <NetworkIcon size={26} />
          <div>
            <h4 style={{ marginBottom: 4 }}>Inspector</h4>
            <p>Pick a node in the tree to inspect thoughts, output and live state.</p>
          </div>
        </div>
        {active.length > 0 && (
          <div>
            <div className="panel-title" style={{ paddingLeft: 0 }}>Currently Running</div>
            <div className="assistant-stream">
              {active.slice(0, 6).map(n => (
                <button key={n.id} className="stream-row" onClick={() => selectNode(n.id)}>
                  <span className={`role-chip role-${n.role}`}>{n.role}</span>
                  <span className="stream-id">{n.id}</span>
                  <span className="stream-state">{n.status}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  const liveOutput = nodeOutputs[node.id];
  const output = liveOutput ?? node.output ?? '';

  return (
    <div className="detail-panel">
      <div className="detail-head">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
          <div className="detail-badges">
            <span className={`role-chip role-${node.role}`}>{node.role}</span>
            <span className="task-chip">{node.tier}</span>
          </div>
          <button className="icon-btn-sm" onClick={() => selectNode(null as any)} title="Close">
            <CloseIcon size={14} />
          </button>
        </div>
        <div className="detail-id ellipsis" title={node.id}>{node.id}</div>
      </div>

      <div className="stat-grid">
        <Stat label="Status" value={node.status} />
        <Stat label="Model" value={node.model_id || '—'} />
        <Stat label="Retries" value={String(node.retries ?? 0)} />
        <Stat label="Reused" value={node.reused ? 'yes' : 'no'} />
        <Stat label="Parent" value={node.parent_id || 'root'} />
        <Stat label="Category" value={node.category || '—'} />
      </div>

      <div>
        <div className="panel-title">Output</div>
        {output ? (
          <MarkdownViewer content={output} />
        ) : (
          <p className="no-messages">No output yet.</p>
        )}
      </div>

      <div>
        <div className="panel-title">Thought Stream</div>
        {node.thought_stream && node.thought_stream.length > 0 ? (
          <div className="thought-stream">
            {node.thought_stream.map((t: any, i: number) => (
              <div key={i} className="thought-entry">
                <span className="thought-time">
                  {new Date(t.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className="thought-text">{t.text}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="no-thoughts">No thoughts recorded.</p>
        )}
      </div>

      {node.error && (
        <div>
          <div className="panel-title" style={{ color: 'var(--error)' }}>Error</div>
          <pre className="error-block">{node.error}</pre>
        </div>
      )}
    </div>
  );
}
