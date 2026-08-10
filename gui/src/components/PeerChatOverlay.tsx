import { useTreeStore } from '../state/treeStore';
import { ChatIcon, CloseIcon } from './icons';

export function PeerChatOverlay() {
  const { peerMessages, isChatOpen, toggleChat } = useTreeStore();

  if (!isChatOpen) {
    return (
      <button
        className="chat-toggle-btn"
        onClick={toggleChat}
        aria-label="Open peer messages"
        style={{ display: 'none' }}
      />
    );
  }

  return (
    <div className="chat-overlay" role="dialog" aria-label="Peer messages">
      <div className="chat-header">
        <span className="chat-header-title">
          <ChatIcon size={14} /> Peer Messages ({peerMessages.length})
        </span>
        <button className="chat-close" onClick={toggleChat} title="Close">
          <CloseIcon size={14} />
        </button>
      </div>
      <div className="chat-messages">
        {peerMessages.length === 0 ? (
          <p className="no-messages">No peer messages yet. Sibling nodes will publish notes here.</p>
        ) : (
          <div className="chat-message-list">
            {peerMessages.slice(-50).map((m: any, i: number) => (
              <div key={i} className="chat-message">
                <div className="chat-message-meta">
                  <span className="chat-from">{m.from_node_id}</span>
                  <span className="chat-time">
                    {new Date(m.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
                <div className="chat-text">{m.text}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
