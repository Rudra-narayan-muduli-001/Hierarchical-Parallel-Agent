import { create } from 'zustand'
import { ChatMessage, Node, Warning, Event } from './types'
import { connectEventStream } from '../api/ws'

interface TreeStore {
  activeTaskId: string | null
  pendingTaskId: string | null
  pendingTaskLabel: string | null
  messages: ChatMessage[]
  nodes: Node[]
  selectedNodeId: string | null
  selectedNode: Node | null
  nodeOutputs: Record<string, string>
  peerMessages: { from_node_id: string; scope: string; text: string; ts: string }[]
  warnings: Warning[]
  wsConnected: boolean
  isChatOpen: boolean
  loading: boolean

  setActiveTaskId: (id: string) => void
  selectNode: (id: string | null) => void
  toggleNode: (id: string) => void
  setNodeOutput: (id: string, output: string) => void
  addPeerMessage: (m: { from_node_id: string; scope: string; text: string; ts: string }) => void
  addWarning: (w: Warning) => void
  dismissWarning: (i: number) => void
  clearWarnings: () => void
  setWsConnected: (b: boolean) => void
  toggleChat: () => void
  submitTask: (task: string, category: string) => Promise<void>
  fetchTree: (taskId: string) => Promise<void>
}

let msgCounter = 0
const nextId = () => `msg_${++msgCounter}_${Date.now()}`

export const useTreeStore = create<TreeStore>((set, get) => ({
  activeTaskId: null,
  pendingTaskId: null,
  pendingTaskLabel: null,
  messages: [],
  nodes: [],
  selectedNodeId: null,
  selectedNode: null,
  nodeOutputs: {},
  peerMessages: [],
  warnings: [],
  wsConnected: false,
  isChatOpen: false,
  loading: false,

  setActiveTaskId: (id) => set({ activeTaskId: id }),
  selectNode: (id) => {
    if (!id) { set({ selectedNodeId: null, selectedNode: null }); return }
    const n = get().nodes.find(x => x.id === id) || null
    set({ selectedNodeId: id, selectedNode: n })
  },
  toggleNode: (id) => set((s) => ({ nodes: s.nodes.map(n => n.id === id ? { ...n, expanded: !(n.expanded ?? true) } : n) })),
  setNodeOutput: (id, output) => set((s) => ({ nodeOutputs: { ...s.nodeOutputs, [id]: output } })),
  addPeerMessage: (m) => set((s) => ({ peerMessages: [...s.peerMessages, m] })),
  addWarning: (w) => set((s) => ({ warnings: [...s.warnings, w] })),
  dismissWarning: (i) => set((s) => ({ warnings: s.warnings.filter((_, idx) => idx !== i) })),
  clearWarnings: () => set({ warnings: [] }),
  setWsConnected: (b) => set({ wsConnected: b }),
  toggleChat: () => set((s) => ({ isChatOpen: !s.isChatOpen })),

  submitTask: async (task, category) => {
    const userMsg: ChatMessage = { id: nextId(), role: 'user', content: task, status: 'done', ts: new Date().toISOString() }
    const aiId = nextId()
    const aiMsg: ChatMessage = { id: aiId, role: 'assistant', content: '', status: 'thinking', ts: new Date().toISOString(), category }
    set((s) => ({ messages: [...s.messages, userMsg, aiMsg], loading: true }))
    const patch = (p: Partial<ChatMessage>) => set((s) => ({ messages: s.messages.map(m => m.id === aiId ? { ...m, ...p } : m) }))
    try {
      const res = await fetch('/api/tasks', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, category }),
      })
      if (!res.ok) throw new Error(`Submit failed ${res.status}`)
      const data = await res.json()
      if (data.task_id) {
        const label = task.length > 60 ? task.slice(0, 60) + '…' : task
        set({ activeTaskId: data.task_id, pendingTaskId: data.task_id, pendingTaskLabel: label })
        patch({ status: 'done', content: data.output || '', taskId: data.task_id as string, confidence: data.confidence, cost: data.cost_summary })
        const ws = connectEventStream(data.task_id, (ev: Record<string, unknown>) => {
          const type = (ev.type || (ev as unknown as { event_type: string }).event_type) as string
          const d = (ev.data || ev) as Record<string, unknown>
          if (type === 'node_output') {
            const nid = String(d.node_id || '')
            if (nid) {
              get().setNodeOutput(nid, String(d.output || ''))
              if (get().selectedNodeId === nid) get().selectNode(nid)
            }
          }
          if (type === 'peer_message') {
            const from = String(d.from_node_id || d.from || 'unknown')
            get().addPeerMessage({ from_node_id: from, scope: String(d.scope || ''), text: String(d.text || ''), ts: String(d.ts || (ev as Record<string, unknown>).ts || new Date().toISOString()) })
          }
          if (type === 'task_warning') {
            get().addWarning({ kind: String(d.kind || 'failure_threshold'), message: String(d.message || `Failure threshold — ${String(d.failure_percent ?? '')}%`) })
          }
          if (type === 'task_degraded') {
            get().addWarning({ kind: 'degraded', message: `Degraded — ${String(d.kind || '')}` })
          }
          if (type === 'task_failed') {
            get().addWarning({ kind: 'error', message: `Task failed — ${String(d.reason || 'zero models')}` })
          }
          if (type === 'node_status_changed' || type === 'node_created' || type === 'node_replaced' || type === 'node_error' || type === 'task_completed' || type === 'task_failed') {
            const tid = String((d.task_id as string) || (d.taskId as string) || get().activeTaskId || data.task_id)
            if (tid) get().fetchTree(tid)
          }
          if (type === 'task_completed' || type === 'task_failed') {
            set({ pendingTaskId: null })
          }
        }, () => get().setWsConnected(true))
        // fallback fetch + close after completed: poll tree, ws auto closes after fetch
        get().fetchTree(data.task_id).finally(() => {
          set({ pendingTaskId: null })
          // keep ws open a bit to receive live events; close after 2s if still open
          setTimeout(() => { try { ws.close(); } catch { /* */ } get().setWsConnected(false) }, 8000)
        })
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Submission failed'
      patch({ status: 'error', error: msg })
      set({ pendingTaskId: null })
    } finally {
      set({ loading: false })
    }
  },

  fetchTree: async (taskId) => {
    try {
      const r = await fetch(`/api/tasks/${taskId}/tree`)
      const data = await r.json()
      if (data.nodes) {
        const prev = new Map(get().nodes.map(n => [n.id, n.expanded]))
        const nodes: Node[] = (data.nodes as Node[]).map(n => ({ ...n, expanded: prev.get(n.id) ?? true }))
        set({ nodes })
        const sel = get().selectedNodeId
        if (sel) {
          const found = nodes.find(n => n.id === sel) || null
          set({ selectedNode: found })
        }
      }
    } catch (e) {
      console.error('fetchTree failed', e)
    }
  },
}))
