import { useEffect, useState } from 'react'
import { useTreeStore } from '../state/treeStore'
import { MessageIcon, XIcon } from './icons'

export function PeerChatOverlay() {
  const { peerMessages, isChatOpen, toggleChat } = useTreeStore()
  const [isMounted, setIsMounted] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

  useEffect(() => {
    if (isChatOpen) {
      setIsMounted(true)
      setIsClosing(false)
    } else if (isMounted) {
      setIsClosing(true)
      const timer = setTimeout(() => {
        setIsMounted(false)
        setIsClosing(false)
      }, 200)
      return () => clearTimeout(timer)
    }
  }, [isChatOpen, isMounted])

  if (!isMounted) return null

  return (
    <>
      <button className={`fab transition-transform ${isClosing ? 'animate-scale-out' : 'animate-bounce-in'} pressable`} onClick={toggleChat} aria-label="Team chat">
        <MessageIcon size={14} />
        Team Chat
        {peerMessages.length > 0 && <span className="fab-badge animate-bounce-in">{peerMessages.length}</span>}
      </button>

      {isMounted && (
        <div className={`chat-overlay ${isClosing ? 'animate-scale-out' : 'animate-scale-in'} transition-all`} role="dialog" aria-label="Team chat" style={{ animationDuration: '200ms' }}>
          <div className="chat-overlay-head">
            <div className="chat-overlay-title"><MessageIcon size={13} /> Team chat · agents talking</div>
            <button className="icon-btn-sm pressable" onClick={toggleChat} aria-label="Close"><XIcon size={13} /></button>
          </div>
          <div className="chat-messages">
            {peerMessages.length === 0 ? (
              <p className="no-data animate-fade-in" style={{ textAlign: 'center', padding: 16, animationDelay: '80ms' }}>No peer messages yet. When two agents of the same rank share context, it appears here.</p>
            ) : (
              <div className="chat-msg-list">
                {peerMessages.map((m, i) => (
                  <div key={i} className="chat-msg animate-slide-down stagger-1" style={{ animationDelay: `${i * 30}ms` }}>
                    <div className="chat-msg-meta">
                      <span className="chat-from">{m.from_node_id}</span>
                      <span className="chat-time">{formatTime(m.ts)} · {m.scope}</span>
                    </div>
                    <div className="chat-text">{m.text}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

function formatTime(ts: string) {
  try { return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) } catch { return ts }
}
