import { useTreeStore } from '../state/treeStore'
import { MessageIcon, XIcon } from './icons'

export function PeerChatOverlay() {
  const { peerMessages, isChatOpen, toggleChat } = useTreeStore()

  return (
    <>
      <button className="fab" onClick={toggleChat} aria-label="Team chat">
        <MessageIcon size={14} />
        Team Chat
        {peerMessages.length > 0 && <span className="fab-badge">{peerMessages.length}</span>}
      </button>

      {isChatOpen && (
        <div className="chat-overlay" role="dialog" aria-label="Team chat">
          <div className="chat-overlay-head">
            <div className="chat-overlay-title"><MessageIcon size={13} /> Team chat · agents talking</div>
            <button className="icon-btn-sm" onClick={toggleChat} aria-label="Close"><XIcon size={13} /></button>
          </div>
          <div className="chat-messages">
            {peerMessages.length === 0 ? (
              <p className="no-data" style={{ textAlign: 'center', padding: 16 }}>No peer messages yet. When two agents of the same rank share context, it appears here.</p>
            ) : (
              <div className="chat-msg-list">
                {peerMessages.map((m, i) => (
                  <div key={i} className="chat-msg">
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
