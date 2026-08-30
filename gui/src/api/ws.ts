export function connectEventStream(
  taskId: string,
  onEvent: (event: Record<string, unknown>) => void,
  onOpen: () => void = () => {},
  onClose: () => void = () => {}
): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${proto}//${window.location.host}/api/ws/tasks/${taskId}`)
  ws.onopen = () => onOpen()
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data)
      onEvent(data)
    } catch (err) {
      console.error('WS parse failed', err)
    }
  }
  ws.onclose = () => onClose()
  ws.onerror = (e) => console.error('WS error', e)
  return ws
}

export async function fetchConfig() {
  const r = await fetch('/api/config')
  if (!r.ok) throw new Error(`config ${r.status}`)
  return r.json()
}
