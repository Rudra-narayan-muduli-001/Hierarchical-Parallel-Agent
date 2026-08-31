export type NodeRole = 'boss' | 'manager' | 'supervisor' | 'labour'
export type NodeStatus = 'idle' | 'assigned' | 'thinking' | 'executing' | 'waiting_children' | 'synthesizing' | 'completed' | 'failed' | 'replaced' | 'degraded' | 'running' | 'pending' | 'ready'

export interface ThoughtEntry {
  ts: string
  text: string
}

export interface Node {
  id: string
  role: NodeRole
  category?: string
  tier?: string
  model_id?: string
  reused?: boolean
  parent_id?: string | null
  children_ids?: string[]
  status: NodeStatus
  thought_stream?: ThoughtEntry[]
  output?: string | null
  error?: string | null
  retries?: number
  expanded?: boolean
  replaced_history?: { from_model: string; to_model: string; reason: string; ts: string }[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  status: 'sending' | 'done' | 'error' | 'thinking'
  ts: string
  taskId?: string
  category?: string
  confidence?: number
  cost?: Record<string, unknown>
  error?: string
}

export interface Event {
  type: string
  data: Record<string, unknown>
  ts: string
}

export interface Warning {
  kind: string
  message: string
}
