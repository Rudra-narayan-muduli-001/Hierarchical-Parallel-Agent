const WS_BASE = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

export function connectEventStream(
  taskId: string,
  onEvent: (event: any) => void,
  onOpen: () => void = () => {},
  onClose: () => void = () => {}
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}//${window.location.host}/api/ws/tasks/${taskId}`);

  ws.onopen = () => {
    onOpen();
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onEvent(data);
    } catch (err) {
      console.error('Failed to parse WS event:', err);
    }
  };

  ws.onclose = () => {
    onClose();
  };

  ws.onerror = (err) => {
    console.error('WebSocket error:', err);
  };

  return ws;
}

export async function submitTask(task: string, category: string) {
  const res = await fetch('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, category }),
  });
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
  return res.json();
}

export async function fetchConfig() {
  const res = await fetch('/api/config');
  if (!res.ok) throw new Error(`Config fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchTaskTree(taskId: string) {
  const res = await fetch(`/api/tasks/${taskId}/tree`);
  if (!res.ok) throw new Error(`Tree fetch failed: ${res.status}`);
  return res.json();
}