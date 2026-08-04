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