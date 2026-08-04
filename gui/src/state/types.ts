export interface Node {
  id: string;
  role: string;
  category: string;
  tier: string;
  model_id: string;
  parent_id: string | null;
  children_ids: string[];
  status: string;
  output: string | null;
  error: string | null;
  thought_stream: ThoughtEntry[];
  retries: number;
  reused: boolean;
  expanded?: boolean;
}

export interface ThoughtEntry {
  ts: string;
  text: string;
}

export interface Event {
  type: string;
  data: Record<string, any>;
  ts: string;
}

export interface PeerMessage {
  from_node_id: string;
  scope: string;
  text: string;
  ts: string;
}

export interface Warning {
  kind: string;
  message: string;
}

export interface TaskSubmitResponse {
  task_id: string;
  output: string;
  confidence: number;
  cost_summary: Record<string, any>;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
}

export interface ConfigResponse {
  categories: string[];
  models: ModelConfig[];
  tiers: string[];
}

export interface ModelConfig {
  id: string;
  tier: string;
  context_window: number;
  rate_limit_rpm: number | null;
}