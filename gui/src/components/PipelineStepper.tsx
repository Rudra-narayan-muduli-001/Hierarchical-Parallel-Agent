import { useMemo } from 'react'
import { useTreeStore } from '../state/treeStore'
import { SearchIcon, CrownIcon, UsersIcon, BranchIcon, BoltIcon, MergeIcon, CheckIcon, AlertIcon, ActivityIcon } from './icons'
import { Node } from '../state/types'

type StepState = 'pending' | 'active' | 'done' | 'failed'

interface StepDef {
  title: string
  sub: string
  icon: React.ReactNode
}

const STEPS: StepDef[] = [
  { title: 'Understanding your task', sub: 'Figuring out what kind of work this is', icon: <SearchIcon size={13} /> },
  { title: 'Director planning', sub: 'Breaking the task into smaller pieces', icon: <CrownIcon size={13} /> },
  { title: 'Assembling teams', sub: 'Picking the right specialists', icon: <UsersIcon size={13} /> },
  { title: 'Coordinating work', sub: 'Coordinators organizing the workers', icon: <BranchIcon size={13} /> },
  { title: 'Workers running', sub: 'Specialists doing the actual work', icon: <BoltIcon size={13} /> },
  { title: 'Combining results', sub: 'Merging answers & fixing disagreements', icon: <MergeIcon size={13} /> },
  { title: 'Delivering answer', sub: 'Final answer ready for you', icon: <CheckIcon size={13} /> },
]

function deriveStates(nodes: Node[], loading: boolean, hasOutput: boolean): StepState[] {
  if (!nodes.length) {
    return STEPS.map((_, i) => (i === 0 && loading ? 'active' as StepState : 'pending' as StepState))
  }
  const byRole = (r: string) => nodes.filter(n => n.role === r)
  const hasFailed = (arr: Node[]) => arr.some(n => n.status === 'failed')
  const allDone = (arr: Node[]) => arr.length > 0 && arr.every(n => n.status === 'completed')
  const anyRunning = (arr: Node[]) => arr.some(n => ['executing', 'running', 'thinking', 'synthesizing', 'waiting_children', 'assigned'].includes(n.status))

  const boss = byRole('boss')
  const mgrs = byRole('manager')
  const sups = byRole('supervisor')
  const labs = byRole('labour')

  const s0: StepState = nodes.length > 0 ? 'done' : loading ? 'active' : 'pending'
  const s1: StepState = boss.length === 0 ? 'pending' : hasFailed(boss) ? 'failed' : anyRunning(boss) ? 'active' : 'done'
  const s2: StepState = mgrs.length === 0 ? (s1 === 'done' ? 'active' : 'pending') : hasFailed(mgrs) ? 'failed' : anyRunning(mgrs) ? 'active' : allDone(mgrs) ? 'done' : 'active'
  const s3: StepState = sups.length === 0 ? (s2 === 'done' ? 'active' : 'pending') : hasFailed(sups) ? 'failed' : anyRunning(sups) ? 'active' : allDone(sups) ? 'done' : 'active'
  const s4: StepState = labs.length === 0 ? (s3 === 'done' ? 'pending' : 'pending') : labs.some(n => ['executing', 'running'].includes(n.status)) ? 'active' : hasFailed(labs) ? 'failed' : allDone(labs) ? 'done' : labs.length > 0 ? 'active' : 'pending'
  // combining: any synthesizing above labour
  const synthesizing = nodes.some(n => n.status === 'synthesizing')
  const s5: StepState = synthesizing ? 'active' : (hasOutput || (boss[0]?.status === 'completed' && labs.length > 0 && allDone(labs)) ? 'done' : s4 === 'done' ? 'active' : 'pending')
  const s6: StepState = hasOutput ? 'done' : (s5 === 'done' && !synthesizing ? 'active' : 'pending')

  return [s0, s1, s2, s3, s4, s5, s6]
}

export function PipelineStepper() {
  const { nodes, loading, messages } = useTreeStore()
  const hasOutput = useMemo(() => messages.some(m => m.role === 'assistant' && m.status === 'done' && m.content), [messages])
  const states = useMemo(() => deriveStates(nodes, loading, !!hasOutput), [nodes, loading, hasOutput])

  // live log: last 5 interesting node statuses
  const liveLog = useMemo(() => {
    const last = [...nodes].sort((a, b) => (a.id > b.id ? -1 : 1)).slice(0, 5)
    if (!last.length) return []
    return last.map(n => ({
      id: n.id,
      text: `${labelFor(n)} ${humanStatus(n.status)}`,
      status: n.status,
    }))
  }, [nodes])

  return (
    <div className="panel">
      <div className="panel-title"><ActivityIcon size={12} /> How it works</div>
      <div className="stepper">
        {STEPS.map((step, i) => {
          const state = states[i]
          return (
            <div key={i} className="step-row">
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div className={`step-dot ${state}`}>
                  {state === 'done' ? <CheckIcon size={12} /> : state === 'failed' ? <AlertIcon size={12} /> : step.icon}
                </div>
                <div className={`step-line ${state === 'done' ? 'done' : state === 'active' ? 'active' : ''}`} />
              </div>
              <div className="step-body">
                <div className="step-title">{step.title}</div>
                <div className="step-sub">{step.sub}</div>
                {state === 'active' && <div className="step-shimmer" />}
                <div className={`step-badge ${state === 'active' ? 'live' : state === 'done' ? 'done' : state === 'failed' ? 'failed' : ''}`}>
                  {state === 'done' ? '✓ Done' : state === 'active' ? '● Live' : state === 'failed' ? '✕ Needs attention' : '○ Waiting'}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {liveLog.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div className="panel-title" style={{ marginBottom: 8 }}>Live log</div>
          <div className="live-log">
            {liveLog.map(l => (
              <div key={l.id} className="live-item">
                <span className={`tree-dot status-${l.status}`} style={{ marginTop: 4 }} />
                <span className="ellipsis">{l.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function labelFor(n: Node) {
  const role = n.role === 'boss' ? 'Director' : n.role === 'manager' ? 'Team Lead' : n.role === 'supervisor' ? 'Coordinator' : 'Worker'
  return `${role} ${n.id.slice(0, 8)}`
}
function humanStatus(s: string) {
  if (s === 'completed') return '✓ finished'
  if (s === 'executing' || s === 'running') return '… running'
  if (s === 'thinking' || s === 'synthesizing') return '… synthesizing'
  if (s === 'waiting_children') return '… waiting for workers'
  if (s === 'failed') return '✕ failed — retrying'
  if (s === 'assigned' || s === 'idle') return '— queued'
  return `— ${s}`
}
