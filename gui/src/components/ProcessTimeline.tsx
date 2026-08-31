import { useMemo } from 'react'
import { useTreeStore } from '../state/treeStore'
import { Node } from '../state/types'

type DotState = 'pending' | 'active' | 'done' | 'failed'
const LABELS = ['Understand', 'Director', 'Teams', 'Coordinate', 'Workers', 'Combine', 'Deliver']

function derive(nodes: Node[], hasOutput: boolean, loading: boolean): DotState[] {
  if (!nodes.length) return LABELS.map((_, i) => (i === 0 && loading ? 'active' : 'pending'))
  const by = (r: string) => nodes.filter(n => n.role === r)
  const any = (arr: Node[], statuses: string[]) => arr.some(n => statuses.includes(n.status))
  const allDone = (arr: Node[]) => arr.length > 0 && arr.every(n => n.status === 'completed')
  const boss = by('boss'), mgr = by('manager'), sup = by('supervisor'), lab = by('labour')
  const active = ['executing', 'running', 'thinking', 'synthesizing', 'waiting_children', 'assigned']
  const s0: DotState = nodes.length ? 'done' : loading ? 'active' : 'pending'
  const s1: DotState = !boss.length ? 'pending' : any(boss, ['failed']) ? 'failed' : any(boss, active) ? 'active' : 'done'
  const s2: DotState = !mgr.length ? (s1 === 'done' ? 'active' : 'pending') : any(mgr, ['failed']) ? 'failed' : any(mgr, active) ? 'active' : allDone(mgr) ? 'done' : 'active'
  const s3: DotState = !sup.length ? (s2 === 'done' ? 'active' : 'pending') : any(sup, ['failed']) ? 'failed' : any(sup, active) ? 'active' : allDone(sup) ? 'done' : 'active'
  const s4: DotState = !lab.length ? 'pending' : any(lab, ['executing', 'running']) ? 'active' : any(lab, ['failed']) ? 'failed' : allDone(lab) ? 'done' : 'active'
  const synth = nodes.some(n => n.status === 'synthesizing')
  const s5: DotState = synth ? 'active' : hasOutput ? 'done' : s4 === 'done' ? 'active' : 'pending'
  const s6: DotState = hasOutput ? 'done' : s5 === 'done' && !synth ? 'active' : 'pending'
  return [s0, s1, s2, s3, s4, s5, s6]
}

export function ProcessTimeline() {
  const { nodes, messages, loading } = useTreeStore()
  const hasOutput = useMemo(() => messages.some(m => m.role === 'assistant' && m.status === 'done' && m.content), [messages])
  const states = useMemo(() => derive(nodes, !!hasOutput, loading), [nodes, hasOutput, loading])
  if (!nodes.length && !loading) return null
  return (
    <div className="timeline-bar">
      {LABELS.map((label, i) => (
        <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="tl-step" style={{ opacity: states[i] === 'pending' ? 0.6 : 1 }}>
            <span className={`tl-dot ${states[i]}`} />
            {label}
          </span>
          {i < LABELS.length - 1 && <span className="tl-arrow">→</span>}
        </span>
      ))}
    </div>
  )
}
