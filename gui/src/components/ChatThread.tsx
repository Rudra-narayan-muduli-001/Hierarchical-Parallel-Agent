import { useEffect, useRef, useState } from 'react'
import { useTreeStore } from '../state/treeStore'
import { MarkdownViewer } from './MarkdownViewer'
import { BoltIcon, CopyIcon, AlertIcon } from './icons'

export function ChatThread() {
  const { messages } = useTreeStore()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="chat-scroll" ref={ref}>
        <div className="chat-thread">
          <div className="chat-empty">
            <div className="empty-logo"><BoltIcon size={28} /></div>
            <h2>What should the parliament build?</h2>
            <p>A single task becomes a hierarchy — Director → Team Leads → Coordinators → Workers — with self-healing at every level. Watch it plan, work and recover live.</p>
            <div className="suggestion-grid">
              <Suggestion label="Implement a binary search tree in Python" cat="coding" />
              <Suggestion label="Explain quantum entanglement simply" cat="research" />
              <Suggestion label="Solve: sum of primes below 100" cat="math" />
              <Suggestion label="Draft a launch email for a new feature" cat="writing" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-scroll" ref={ref}>
      <div className="chat-thread">
        {messages.map(m => (
          <div key={m.id} className={`chat-item ${m.role === 'user' ? 'chat-item-user' : ''}`}>
            {m.role === 'assistant' && <div className="avatar avatar-ai"><BoltIcon size={15} /></div>}
            <div className="chat-content">
              {m.role === 'assistant' && m.status !== 'error' && (
                <div className="meta-row">
                  {m.category && <span className="meta-pill">{m.category}</span>}
                  {m.status === 'thinking' && <span className="meta-label">● Thinking…</span>}
                  {m.taskId && <span className="meta-label">Task <strong>{m.taskId}</strong></span>}
                </div>
              )}
              {m.status === 'thinking' ? (
                <div className="msg-thinking"><span className="spinner" /> Director is planning — breaking your task into pieces…</div>
              ) : m.status === 'error' ? (
                <div className="msg-error"><AlertIcon size={14} /><span>{m.error || 'Something went wrong.'}</span></div>
              ) : m.role === 'user' ? (
                <>{m.content}</>
              ) : (
                <div className="assistant-card">
                  <div className="assistant-card-head">
                    <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                      Answer {m.confidence !== undefined ? `· confidence ${Math.round((m.confidence as number) * 100)}%` : ''}
                    </span>
                    <CopyButton text={m.content} />
                  </div>
                  <div className="assistant-card-body">
                    <MarkdownViewer content={m.content} />
                    {m.cost && (
                      <div className="cost-row">
                        {Object.entries(m.cost).map(([k, v]) => (
                          <span key={k} className="cost-pill">{k}: {String(v)}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            {m.role === 'user' && <div className="avatar avatar-user">You</div>}
          </div>
        ))}
      </div>
    </div>
  )
}

function Suggestion({ label, cat }: { label: string; cat: string }) {
  const { submitTask } = useTreeStore()
  return (
    <button className="suggestion-card" onClick={() => submitTask(label, cat)}>
      <span className="suggestion-label">{label}</span>
      <span className="suggestion-cat">{cat}</span>
    </button>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button className="icon-btn-sm" title="Copy answer" onClick={async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1400) }}>
      {copied ? <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--success)' }}>Copied!</span> : <CopyIcon size={14} />}
    </button>
  )
}
