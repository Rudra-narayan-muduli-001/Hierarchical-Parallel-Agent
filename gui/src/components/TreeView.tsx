import { useEffect, useMemo } from 'react';
import { useTreeStore } from '../state/treeStore';
import { Node } from '../state/types';
import { NetworkIcon, ChevronRightIcon } from './icons';

function NodeRow({ node, depth }: { node: Node; depth: number }) {
  const { selectedNodeId, selectNode, toggleNode, nodes } = useTreeStore();
  const children = useMemo(
    () => nodes.filter(n => n.parent_id === node.id),
    [nodes, node.id]
  );
  const hasChildren = children.length > 0;
  const expanded = node.expanded ?? true;
  const isSelected = selectedNodeId === node.id;

  return (
    <>
      <button
        className={`tree-node-row ${isSelected ? 'selected' : ''}`}
        onClick={() => selectNode(node.id)}
        style={{ paddingLeft: 10 + depth * 14 }}
      >
        <span className={`tree-toggle ${expanded ? 'open' : ''} ${hasChildren ? '' : 'placeholder'}`}>
          <ChevronRightIcon size={12} />
        </span>
        <span className={`tree-dot status-${node.status}`} title={node.status} />
        <span className={`role-chip role-${node.role}`}>{node.role}</span>
        <span className="tree-id ellipsis" title={node.id}>{node.id}</span>
        <span className="tree-tier">{node.tier}</span>
        {hasChildren && (
          <span className="tree-toggle" onClick={(e) => { e.stopPropagation(); toggleNode(node.id); }} style={{ marginLeft: 'auto', display: 'flex' }}>
            <ChevronRightIcon size={12} />
          </span>
        )}
      </button>
      {expanded && children.map((c) => <NodeRow key={c.id} node={c} depth={depth + 1} />)}
    </>
  );
}

export function TreeView() {
  const { nodes, activeTaskId, fetchTree } = useTreeStore();

  useEffect(() => {
    if (activeTaskId) fetchTree(activeTaskId);
  }, [activeTaskId]);

  const roots = useMemo(() => nodes.filter(n => !n.parent_id), [nodes]);

  return (
    <div className="panel">
      <div className="panel-title">
        <NetworkIcon size={13} /> Task Tree
      </div>
      {nodes.length === 0 ? (
        <p className="no-messages">Submit a task to see the hierarchy.</p>
      ) : (
        <div className="tree">
          {roots.map((n) => <NodeRow key={n.id} node={n} depth={0} />)}
        </div>
      )}
    </div>
  );
}
