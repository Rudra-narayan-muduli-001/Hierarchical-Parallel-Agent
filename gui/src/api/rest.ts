export async function submitTask(task: string, category: string) {
  const r = await fetch('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, category }),
  })
  if (!r.ok) throw new Error(`Submit failed ${r.status}`)
  return r.json()
}

export async function fetchTree(taskId: string) {
  const r = await fetch(`/api/tasks/${taskId}/tree`)
  if (!r.ok) throw new Error(`Tree ${r.status}`)
  return r.json()
}

export async function fetchConfig() {
  const r = await fetch('/api/config')
  if (!r.ok) throw new Error(`Config ${r.status}`)
  return r.json()
}
