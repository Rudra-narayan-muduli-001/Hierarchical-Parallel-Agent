import { useEffect, useRef } from 'react';
import { useTreeStore } from '../state/treeStore';
import { ChatMessage } from '../state/types';
import { MarkdownViewer } from './MarkdownViewer';
import { BrainIcon, CopyIcon, CheckIcon, AlertIcon } from './icons';
import { useState } from 'react';

function Spinner() {
  return <span className="spinner" aria-label="thinking" />;
}

function MessageMeta({ msg }: { msg: ChatMessage }) {
  const [copied, setCopied] = useState(false);
  const cost = msg.cost;
  const costText = cost && Object.keys(cost).length > 0
    ? JSON.stringify(cost)
        .replace(/[{}\[\]"]+/g, ' ')
        .trim()
    : null;

  const copy = () => {
    navigator.clipboard.writeText(msg.content || '').catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="msg-meta">
      {msg.category && <span className="meta-pill">{msg.category}</span>}
      {(msg.confidence ?? 0) > 0 && (
        <span className="meta-label">
          <strong>{Math.round((msg.confidence ?? 0) * 100)}%</strong> confidence
        </span>
      )}
      {costText && (
        <span className="meta-label meta-cost ellipsis">cost: {costText}</span>
      )}
      {msg.taskId && <span className="task-chip">{msg.taskId}</span>}
      <span className="meta-sep" style={{ marginLeft: 'auto' }} />
      <button className="icon-btn-sm" onClick={copy} title="Copy response">
        {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
      </button>
    </div>
  );
}

function MessageItem({ msg }: { msg: ChatMessage }) {
  if (msg.role === 'user') {
    return (
      <div className="chat-item chat-item-user">
        <div className="chat-content">{msg.content}</div>
        <div className="avatar avatar-user">U</div>
      </div>
    );
  }

  return (
    <div className="chat-item chat-item-ai">
      <div className="avatar avatar-ai">
        <BrainIcon size={17} />
      </div>
      <div className="chat-content">
        {(msg.status === 'sending' || msg.status === 'running') ? (
          <div className="msg-thinking">
            <Spinner />
            <span>Assembling the hierarchy&hellip;</span>
          </div>
        ) : msg.status === 'error' ? (
          <div className="msg-error">
            <AlertIcon size={15} />
            <div>{msg.error || 'Something went wrong.'}</div>
          </div>
        ) : (
          <>
            <MessageMeta msg={msg} />
            <MarkdownViewer content={msg.content || '_No output returned._'} />
          </>
        )}
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  { text: 'Write a Python function that finds duplicate files by content hash', cat: 'coding' },
  { text: 'Research the key differences between React Server and Client Components', cat: 'research' },
  { text: 'Explain the quicksort algorithm and its time complexity', cat: 'coding' },
  { text: 'Compare groq vs openai inference latency for small models', cat: 'research' },
];

export function ChatThread() {
  const { messages, pendingTaskId, pendingTaskLabel, submitTask, loading } = useTreeStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, pendingTaskId]);

  return (
    <div className="chat-scroll" ref={scrollRef}>
      <div className="chat-thread">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-logo">
              <BrainIcon size={32} />
            </div>
            <div>
              <h2>How can the hierarchy help today?</h2>
              <p>
                Submit a task and watch a Boss → Manager → Supervisor → Labour tree
                break it down, execute, and iterate — live.
              </p>
            </div>
            <div className="suggestion-grid">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  className="suggestion-card"
                  disabled={loading}
                  onClick={() => submitTask(s.text, s.cat)}
                >
                  <span className="suggestion-label">{s.text}</span>
                  <span className="suggestion-cat">{s.cat}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((m) => (
              <MessageItem key={m.id} msg={m} />
            ))}
            {pendingTaskId && (
              <div className="msg-thinking">
                <Spinner />
                <span>
                  {pendingTaskLabel ? `“${pendingTaskLabel}” · ` : ''}
                  {pendingTaskId} — not yet returned, stream waiting…
                </span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
