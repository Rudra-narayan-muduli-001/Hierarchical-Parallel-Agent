import { useEffect, useRef, useState } from 'react'
import { useTreeStore } from '../state/treeStore'
import { ChatMessage } from '../state/types'
import { MarkdownViewer } from './MarkdownViewer'
import { BoltIcon, CopyIcon, AlertIcon } from './icons'

function ChatItem({ message, index, totalCount }: { message: ChatMessage; index: number; totalCount: number }) {
  const [isExiting, setIsExiting] = useState(false)
  const [hasEntered, setHasEntered] = useState(false)

  useEffect(() => {
    setHasEntered(true)
  }, [])

  const handleAnimationEnd = (e: React.AnimationEvent) => {
    if (e.animationName === 'fadeOut' || e.animationName === 'slideUp') {
      // The parent will handle removal via key changes
    }
  }

  const isUser = message.role === 'user'
  const isThinking = message.status === 'thinking'
  const isError = message.status === 'error'

  const enterAnimation = hasEntered ? 'animate-bounce-in' : ''
  const exitAnimation = isExiting ? 'animate-slide-up' : ''

  if (message.id.startsWith('exiting_')) return null

  return (
    <div key={message.id} className={`chat-item ${isUser ? 'chat-item-user' : ''} ${enterAnimation} ${exitAnimation}`} onAnimationEnd={handleAnimationEnd}>
      {message.role === 'assistant' && <div className="avatar avatar-ai"><BoltIcon size={15} /></div>}
      <div className="chat-content">
        {message.role === 'assistant' && message.status !== 'error' && (
          <div className="meta-row">
            {message.category && <span className="meta-pill">{message.category}</span>}
            {message.status === 'thinking' && <span className="meta-label">● Thinking…</span>}
            {message.taskId && <span className="meta-label">Task <strong>{message.taskId}</strong></span>}
          </div>
        )}
        {isThinking ? (
          <div className="msg-thinking"><span className="spinner" /> Director is planning — breaking your task into pieces…</div>
        ) : isError ? (
          <div className="msg-error"><AlertIcon size={14} /><span>{message.error || 'Something went wrong.'}</span></div>
        ) : isUser ? (
          <>{message.content}</>
        ) : (
          <div className="assistant-card">
            <div className="assistant-card-head">
              <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Answer {message.confidence !== undefined ? `· confidence ${Math.round((message.confidence as number) * 100)}%` : ''}
              </span>
              <CopyButton text={message.content} />
            </div>
            <div className="assistant-card-body">
              <MarkdownViewer content={message.content} />
              {message.cost && (
                <div className="cost-row">
                  {Object.entries(message.cost).map(([k, v]) => (
                    <span key={k} className="cost-pill">{k}: {String(v)}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      {isUser && <div className="avatar avatar-user">You</div>}
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button className="icon-btn-sm pressable" title="Copy answer" onClick={async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1400) }}>
      {copied ? <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--success)' }}>Copied!</span> : <CopyIcon size={14} />}
    </button>
  )
}

function Suggestion({ label, cat }: { label: string; cat: string }) {
  const { submitTask } = useTreeStore()
  return (
    <button className="suggestion-card animate-slide-down interactive pressable" style={{ animationDelay: `${cat === 'coding' ? 0 : cat === 'research' ? 60 : cat === 'math' ? 120 : 180}ms` }} onClick={() => submitTask(label, cat)}>
      <span className="suggestion-label">{label}</span>
      <span className="suggestion-cat">{cat}</span>
    </button>
  )
}

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
          <div className="chat-empty animate-fade-in">
            <div className="empty-logo animate-bounce-in"><BoltIcon size={28} /></div>
            <h2 className="animate-slide-down" style={{ animationDelay: '100ms' }}>What should the parliament build?</h2>
            <p className="animate-slide-down" style={{ animationDelay: '180ms' }}>A single task becomes a hierarchy — Director → Team Leads → Coordinators → Workers — with self-healing at every level. Watch it plan, work and recover live.</p>
            <div className="suggestion-grid animate-slide-down" style={{ animationDelay: '260ms' }}>
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
        {messages.map((m, i) => (
          <ChatItem key={m.id} message={m} index={i} totalCount={messages.length} />
        ))}
      </div>
    </div>
  )
}
