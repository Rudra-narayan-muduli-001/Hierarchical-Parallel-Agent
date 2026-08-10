import { create } from 'zustand';
import { Node, ChatMessage, Event } from './types';
import { connectEventStream } from '../api/ws';

interface TreeStore {
  activeTaskId: string | null;
  messages: ChatMessage[];
  pendingTaskId: string | null;
  pendingTaskLabel: string | null;
  nodes: Node[];
  selectedNodeId: string | null;
  selectedNode: Node | null;
  nodeOutputs: Record<string, string>;
  peerMessages: any[];
  warnings: any[];
  wsConnected: boolean;
  isChatOpen: boolean;
  loading: boolean;

  // Actions
  setActiveTaskId: (id: string) => void;
  setNodes: (nodes: Node[]) => void;
  selectNode: (nodeId: string) => void;
  toggleNode: (nodeId: string) => void;
  setNodeOutput: (nodeId: string, output: string) => void;
  addPeerMessage: (msg: any) => void;
  addWarning: (warning: any) => void;
  clearWarnings: () => void;
  setWsConnected: (connected: boolean) => void;
  toggleChat: () => void;
  clear: () => void;
  dismissWarning: (index: number) => void;

  // Async
  submitTask: (task: string, category: string) => Promise<void>;
  fetchTree: (taskId: string) => Promise<void>;
}

let msgCounter = 0;
const nextMsgId = () => `msg_${++msgCounter}_${Date.now()}`;

export const useTreeStore = create<TreeStore>((set, get) => ({
  activeTaskId: null,
  messages: [],
  pendingTaskId: null,
  pendingTaskLabel: null,
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
  setNodes: (nodes) => set({ nodes }),
  selectNode: (nodeId) => {
    const node = get().nodes.find(n => n.id === nodeId) || null;
    set({ selectedNodeId: nodeId, selectedNode: node });
  },
  toggleNode: (nodeId) => set((state) => ({
    nodes: state.nodes.map(n =>
      n.id === nodeId ? { ...n, expanded: !n.expanded } : n
    )
  })),
  setNodeOutput: (nodeId, output) => set((state) => ({
    nodeOutputs: { ...state.nodeOutputs, [nodeId]: output }
  })),
  addPeerMessage: (msg) => set((state) => ({
    peerMessages: [...state.peerMessages, msg]
  })),
  addWarning: (warning) => set((state) => ({
    warnings: [...state.warnings, warning]
  })),
  clearWarnings: () => set({ warnings: [] }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  toggleChat: () => set((state) => ({ isChatOpen: !state.isChatOpen })),
  dismissWarning: (index) => set((state) => ({
    warnings: state.warnings.filter((_, i) => i !== index)
  })),
  clear: () => set({
    activeTaskId: null, messages: [], pendingTaskId: null, pendingTaskLabel: null,
    nodes: [], selectedNodeId: null, selectedNode: null,
    nodeOutputs: {}, peerMessages: [], warnings: [], isChatOpen: false, loading: false
  }),

  submitTask: async (task: string, category: string) => {
    const userMsg: ChatMessage = {
      id: nextMsgId(), role: 'user', content: task, status: 'done', ts: new Date().toISOString(),
    };
    const aiMsgId = nextMsgId();
    const aiMsg: ChatMessage = {
      id: aiMsgId, role: 'assistant', content: '', status: 'sending', ts: new Date().toISOString(),
    };
    set((state) => ({ messages: [...state.messages, userMsg, aiMsg], loading: true }));

    const patchAiMsg = (patch: Partial<ChatMessage>) => set((state) => ({
      messages: state.messages.map(m => m.id === aiMsgId ? { ...m, ...patch } : m)
    }));

    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, category }),
      });
      if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
      const data = await res.json();

      if (data.task_id) {
        set({
          activeTaskId: data.task_id,
          pendingTaskId: data.task_id,
          pendingTaskLabel: task.length > 60 ? task.slice(0, 60) + '…' : task,
        });
        patchAiMsg({
          status: 'done',
          content: data.output || '',
          taskId: data.task_id,
          category,
          confidence: data.confidence,
          cost: data.cost_summary,
        });

        // Live event stream for tree/status updates while the tree loads.
        const ws = connectEventStream(data.task_id, (event: Event) => {
          const type = event?.type || (event as any)?.event_type;
          const data = (event as any)?.data || event;
          if (type === 'node_output') {
            const nid = data.node_id;
            get().setNodeOutput(nid, data.output || '');
            if (get().selectedNodeId === nid) {
              get().selectNode(nid);
            }
          }
          if (type === 'peer_message') {
            get().addPeerMessage({ from_node_id: data.from_node_id, scope: data.scope, text: data.text, ts: data.ts });
          }
          if (type === 'task_warning') {
            get().addWarning({ kind: data.kind || 'failure_threshold', message: data.message || `Failure threshold reached (${data.failure_percent ?? ''}%)` });
          }
          if (type === 'task_degraded') {
            get().addWarning({ kind: 'degraded', message: `Degraded hierarchy: ${data.kind}` });
          }
          if (type === 'node_status_changed' || type === 'node_created') {
            get().fetchTree(data.task_id || get().activeTaskId || data.task_id);
          }
          if (type === 'task_completed' || type === 'task_failed') {
            set({ pendingTaskId: null });
            get().fetchTree(data.task_id || get().activeTaskId || data.task_id);
          }
        }, () => get().setWsConnected(true));

        get().fetchTree(data.task_id).finally(() => {
          set({ pendingTaskId: null });
          ws.close();
          get().setWsConnected(false);
        });
      }
    } catch (err: any) {
      patchAiMsg({ status: 'error', error: err.message || 'Submission failed' });
      set({ pendingTaskId: null });
    } finally {
      set({ loading: false });
    }
  },

  fetchTree: async (taskId: string) => {
    try {
      const res = await fetch(`/api/tasks/${taskId}/tree`);
      const data = await res.json();
      if (data.nodes) {
        const prev = get().nodes;
        const expanded = new Map(prev.map(n => [n.id, n.expanded]));
        set({
          nodes: data.nodes.map((n: Node) => ({ ...n, expanded: expanded.get(n.id) ?? true })),
        });
        const sel = get().selectedNodeId;
        if (sel) {
          const node = data.nodes.find((n: Node) => n.id === sel) || null;
          set({ selectedNode: node });
        }
      }
    } catch (err) {
      console.error('Fetch tree failed:', err);
    }
  },
}));
