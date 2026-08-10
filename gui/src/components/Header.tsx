import { useTreeStore } from '../state/treeStore';
import { BrainIcon, ChatIcon } from './icons';

export function Header({ wsConnected }: { wsConnected: boolean }) {
  const { activeTaskId, isChatOpen, toggleChat, peerMessages } = useTreeStore();

  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-mark"><BrainIcon size={18} /></div>
        <div className="brand-name">Parallel<span> Mind</span></div>
      </div>

      <div className="header-right">
        {activeTaskId && <span className="task-chip">{activeTaskId}</span>}
        <span className={`status-pill ${wsConnected ? '' : 'disconnected'}`}>
          <span className={`status-dot ${wsConnected ? 'ok' : 'off'}`} />
          {wsConnected ? 'Live stream' : 'Idle'}
        </span>
        <button
          className="icon-btn"
          onClick={toggleChat}
          title="Peer messages"
          aria-label="Peer messages"
        >
          <ChatIcon size={16} />
          {peerMessages.length > 0 && (
            <span className="chat-toggle-badge" style={{ marginLeft: 4 }}>
              {peerMessages.length}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}
