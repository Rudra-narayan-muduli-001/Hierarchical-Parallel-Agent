import { useMemo } from 'react'
import { useTreeStore } from '../state/treeStore'
import { Node } from '../state/types'
import { NetworkIcon, ChevronRightIcon } from './icons'

function NodeRow({ node, depth }: { node: Node; depth: number }) {
  const { nodes, selectedNodeId, selectNode, toggleNode } = useTreeStore()
  const children = useMemo(() => nodes.filter(n => n.parent_id === node.id), [nodes, node.id])
  const hasChildren = children.length > 0
  const expanded = node.expanded ?? true
  const sel = selectedNodeId === node.id

  return (
    <>
      <button className={`tree-row ${sel ? 'selected' : ''}`} onClick={() => selectNode(node.id)} style={{ paddingLeft: 8 + depth * 14 }}>
        <span className={`tree-chevron ${expanded ? 'open' : ''} ${hasChildren ? '' : 'placeholder'}`} onClick={(e) => { if (hasChildren) { e.stopPropagation(); toggleNode(node.id) } }}>
          <ChevronRightIcon size={11} />
        </span>
        <span className={`tree-dot ${node.status}`} title={node.status} />
        <span className={`role-chip role-${node.role}`} title={plainRole(node.role)}>{node.role}</span>
        <span className="tree-id" title={node.id}>{node.id.slice(0, 12)}</span>
        {hasChildren && <span className="tree-count">×{children.length}</span>}
        <span className="tree-tier">{node.tier || ''}</span>
      </button>
      {expanded && children.map(c => <NodeRow key={c.id} node={c} depth={depth + 1} />)}
    </>
  )
}

function plainRole(r: string) {
  if (r === 'boss') return 'Director — owns the plan'
  if (r === 'manager') return 'Team Lead — splits big tasks'
  if (r === 'supervisor') return 'Coordinator — guides workers'
  return 'Worker — does one job'
}

export function HierarchyTree() {
  const { nodes } = useTreeStore()
  const roots = useMemo(() => nodes.filter(n => !n.parent_id), [nodes])
  const counts = useMemo(() => {
    const c: Record<string, number> = { boss: 0, manager: 0, supervisor: 0, labour: 0 }
    nodes.forEach(n => { if (c[n.role] !== undefined) c[n.role]++ })
    return c
  }, [nodes])

  return (
    <div className="panel">
      <div className="panel-title"><NetworkIcon size={12} /> Hierarchy</div>
      {nodes.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
          <span className="role-chip role-boss">Director {counts.boss}</span>
          <span className="role-chip role-manager">Leads {counts.manager}</span>
          <span className="role-chip role-supervisor">Coords {counts.supervisor}</span>
          <span className="role-chip role-labour">Workers {counts.labour}</span>
        </div>
      )}
      {nodes.length === 0 ? (
        <p className="no-data" style={{ textAlign: 'center', padding: '10px 0' }}>Submit a task to see the hierarchy.</p>
      ) : (
        <div className="tree">{roots.map(r => <NodeRow key={r.id} node={r} depth={0} />)}</div>
      )}
    </div>
  )
}
