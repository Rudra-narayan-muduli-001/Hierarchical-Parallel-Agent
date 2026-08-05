import { useTreeStore } from '../state/treeStore';
import { Node } from '../state/types';

export function NodeDetailPanel() {
  const { selectedNode, nodeOutputs } = useTreeStore();
  const node = selectedNode as (Node & { output?: string }) | null;

  if (!node) {
    return (
      <div className="detail-panel">
        <h3>Node Detail</h3>
        <p className="empty-detail">Click a node in the tree to view details.</p>
      </div>
    );
  }

  const output = nodeOutputs[node.id] || node.output || 'No output yet.';

  return (
    <div className="detail-panel">
      <h3>Node: {node.id}</h3>
      <div className="detail-section">
        <h4>Basic Info</h4>
        <dl>
          <dt>Role</dt><dd>{node.role}</dd>
          <dt>Category</dt><dd>{node.category}</dd>
          <dt>Tier</dt><dd>{node.tier}</dd>
          <dt>Model</dt><dd>{node.model_id}</dd>
          <dt>Status</dt><dd>{node.status}</dd>
          <dt>Reused</dt><dd>{node.reused ? 'Yes' : 'No'}</dd>
          <dt>Retries</dt><dd>{node.retries}</dd>
          <dt>Parent</dt><dd>{node.parent_id || 'None (Root)'}</dd>
        </dl>
      </div>

      <div className="detail-section">
        <h4>Thought Stream</h4>
        <div className="thought-stream">
          {node.thought_stream && node.thought_stream.length > 0 ? (
            node.thought_stream.map((t: any, i: number) => (
              <div key={i} className="thought-entry">
                <span className="thought-time">{new Date(t.ts).toLocaleTimeString()}</span>
                <span className="thought-text">{t.text}</span>
              </div>
            ))
          ) : (
            <p className="no-thoughts">No thoughts recorded.</p>
          )}
        </div>
      </div>

      <div className="detail-section">
        <h4>Output</h4>
        <pre className="output-block">{output}</pre>
      </div>

      {node.error && (
        <div className="detail-section error">
          <h4>Error</h4>
          <pre className="error-block">{node.error}</pre>
        </div>
      )}
    </div>
  );
}
