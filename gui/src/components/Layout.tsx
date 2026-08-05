import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { TreeView } from './TreeView';
import { NodeDetailPanel } from './NodeDetailPanel';
import { PeerChatOverlay } from './PeerChatOverlay';
import { WarningBanner } from './WarningBanner';
import { TaskSubmitForm } from './TaskSubmitForm';
import { useTreeStore } from '../state/treeStore';

export function Layout() {
  const { wsConnected } = useTreeStore();
  return (
    <div className="app-layout">
      <Header wsConnected={wsConnected} />
      <div className="main-container">
        <aside className="sidebar">
          <TaskSubmitForm />
          <WarningBanner />
        </aside>
        <main className="main-content">
          <TreeView />
          <Outlet />
        </main>
        <aside className="detail-panel">
          <NodeDetailPanel />
        </aside>
      </div>
      <PeerChatOverlay />
    </div>
  );
}