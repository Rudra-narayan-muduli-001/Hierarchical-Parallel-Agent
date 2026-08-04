import { create } from 'zustand';
import { Node } from './types';

interface TreeStore {
  activeTaskId: string | null;
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

  // Async
  submitTask: (task: string, category: string) => Promise<void>;
  fetchTree: (taskId: string) => Promise<void>;
}

export const useTreeStore = create<TreeStore>((set, get) => ({
  activeTaskId: null,
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
  clear: () => set({
    activeTaskId: null, nodes: [], selectedNodeId: null,
    nodeOutputs: {}, peerMessages: [], warnings: [], isChatOpen: false, loading: false
  }),

  submitTask: async (task: string, category: string) => {
    set({ loading: true });
    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, category }),
      });
      const data = await res.json();
      if (data.task_id) {
        set({ activeTaskId: data.task_id });
        get().fetchTree(data.task_id);
      }
    } catch (err) {
      console.error('Submit failed:', err);
    } finally {
      set({ loading: false });
    }
  },

  fetchTree: async (taskId: string) => {
    try {
      const res = await fetch(`/api/tasks/${taskId}/tree`);
      const data = await res.json();
      if (data.nodes) {
        set({ nodes: data.nodes });
      }
    } catch (err) {
      console.error('Fetch tree failed:', err);
    }
  },
}));