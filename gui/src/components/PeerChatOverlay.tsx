import { useTreeStore } from '../state/treeStore';

export function PeerChatOverlay() {
  const { peerMessages, isChatOpen, toggleChat } = useTreeStore();

  if (!isChatOpen) {
    return (
      <button className="chat-toggle-btn" onClick={toggleChat}>
        💬 Peer Chat ({peerMessages.length})
      </button>
    );
  }

  return (
    <div className="chat-overlay">
      <div className="chat-header">
        <h4>Peer Messages</h4>
        <button onClick={toggleChat}>✕</button>
      </div>
      <div className="chat-messages">
        {peerMessages.length === 0 ? (
          <p className="no-messages">No peer messages yet.</p>
        ) : (
          peerMessages.map((m: any, i: number) => (
            <div key={i} className="chat-message">
              <span className="chat-from">{m.from_node_id}</span>
              <span className="chat-text">{m.text}</span>
              <span className="chat-time">{new Date(m.ts).toLocaleTimeString()}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
