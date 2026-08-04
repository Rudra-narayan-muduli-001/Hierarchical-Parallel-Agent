import { useEffect, useState, useRef } from 'react';
import { useTreeStore } from '../state/treeStore';
import { Node } from '../state/types';

export function TreeView() {
  const { nodes, activeTaskId, fetchTree } = useTreeStore();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeTaskId) fetchTree(activeTaskId);
  }, [activeTaskId]);

  const rootNodes = nodes.filter(n => !n.parent_id);
  const childrenMap = new Map<string, Node[]>();
  nodes.forEach(n => {
    if (n.parent_id) {
      const arr = childrenMap.get(n.parent_id) || [];
      arr.push(n);
      childrenMap.set(n.parent_id, arr);
    }
  });

  const renderNode = (node: Node, depth: number) => {
    const children = childrenMap.get(node.id) || [];
    const isExpanded = node.expanded || false;
    const hasChildren = children.length > 0;

    return (
      <div key={node.id} className="tree-node" style={{ marginLeft: depth * 20 }}>
        <div
          className={`node-row ${selectedNodeId === node.id ? 'selected' : ''}`}
          onClick={() => {
            setSelectedNodeId(node.id);
            useTreeStore.getState().selectNode(node.id);
          }}
        >
          {hasChildren && (
            <button className="expand-toggle" onClick={(e) => {
              e.stopPropagation();
              useTreeStore.getState().toggleNode(node.id);
            }}>
              {isExpanded ? '▼' : '▶'}
            </button>
          )}
          <span className={`status-dot status-${node.status}`} />
          <span className="node-info">
            <strong>{node.id}</strong> ({node.role}, {node.tier})
          </span>
          <span className="node-model">{node.model_id}</span>
        </div>
        {isExpanded && children.map(c => renderNode(c, depth + 1))}
      </div>
    );
  };

  return (
    <div className="tree-view" ref={containerRef}>
      <h3>Task Tree</h3>
      <div className="tree-container">
        {rootNodes.length === 0 ? (
          <p className="empty-tree">No tree data. Submit a task to begin.</p>
        ) : (
          rootNodes.map(n => renderNode(n, 0))
        )}
      </div>
    </div>
  );
}
