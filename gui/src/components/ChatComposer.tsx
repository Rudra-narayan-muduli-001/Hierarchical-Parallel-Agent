import { useEffect, useState, useRef } from 'react'
import { useTreeStore } from '../state/treeStore'
import { SendIcon, AlertIcon } from './icons'

const CATEGORIES = ['auto', 'coding', 'math', 'research', 'writing']

export function ChatComposer() {
  const { submitTask, loading } = useTreeStore()
  const [text, setText] = useState('')
  const [category, setCategory] = useState('auto')
  const [error, setError] = useState<string | null>(null)
  const taRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (taRef.current) {
      taRef.current.style.height = 'auto'
      taRef.current.style.height = Math.min(taRef.current.scrollHeight, 120) + 'px'
    }
  }, [text])

  const send = async () => {
    const t = text.trim()
    if (!t || loading) return
    setError(null)
    const cat = category === 'auto' ? '' : category
    try {
      setText('')
      await submitTask(t, cat || 'coding')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to submit')
    }
  }

  return (
    <div className="composer">
      {error && <div className="composer-error"><AlertIcon size={13} /><span>{error}</span></div>}
      <div className="composer-box">
        <div className="composer-stack">
          <textarea
            ref={taRef}
            className="composer-textarea"
            placeholder="Describe your task — e.g. 'Build a snake game in Python'…"
            rows={1}
            value={text}
            disabled={loading}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <div className="category-pills">
              {CATEGORIES.map(c => (
                <button key={c} className={`cat-pill ${category === c ? 'active' : ''}`} onClick={() => setCategory(c)}>{c}</button>
              ))}
            </div>
            <span className="composer-hint">{loading ? 'Working…' : '↵ Enter to send · ⇧↵ new line'}</span>
          </div>
        </div>
        <button className="send-btn" onClick={send} disabled={loading || !text.trim()} aria-label="Send">
          <SendIcon size={16} />
        </button>
      </div>
    </div>
  )
}
