import { useTreeStore } from '../state/treeStore';

export function Header({ wsConnected }: { wsConnected: boolean }) {
  const { activeTaskId } = useTreeStore();
  return (
    <header className="app-header">
      <h1>Parallel Mind</h1>
      <div className="header-status">
        <span className={`ws-indicator ${wsConnected ? 'connected' : 'disconnected'}`} />
        {activeTaskId && <span className="task-id">Task: {activeTaskId}</span>}
      </div>
    </header>
  );
}
