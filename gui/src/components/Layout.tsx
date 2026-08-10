import { Header } from './Header';
import { TreeView } from './TreeView';
import { NodeDetailPanel } from './NodeDetailPanel';
import { PeerChatOverlay } from './PeerChatOverlay';
import { WarningBanner } from './WarningBanner';
import { ChatThread } from './ChatThread';
import { ChatComposer } from './ChatComposer';
import { useTreeStore } from '../state/treeStore';

export function Layout() {
  const { wsConnected } = useTreeStore();

  return (
    <div className="app">
      <Header wsConnected={wsConnected} />

      <div className="app-body">
        <aside className="sidebar">
          <TreeView />
          <WarningBanner />
        </aside>

        <main className="chat-main">
          <ChatThread />
          <ChatComposer />
        </main>

        <aside className="inspector">
          <NodeDetailPanel />
        </aside>
      </div>

      <PeerChatOverlay />
    </div>
  );
}
