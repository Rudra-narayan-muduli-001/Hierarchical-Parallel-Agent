import { useState } from 'react';
import { useTreeStore } from '../state/treeStore';

export function TaskSubmitForm() {
  const { submitTask, activeTaskId, wsConnected } = useTreeStore();
  const [taskText, setTaskText] = useState('');
  const [category, setCategory] = useState('coding');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await submitTask(taskText, category);
      setTaskText('');
    } catch (err: any) {
      setError(err.message || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="task-form">
      <h4>Submit Task</h4>
      <textarea
        value={taskText}
        onChange={(e) => setTaskText(e.target.value)}
        placeholder="Enter your task..."
        rows={4}
        disabled={loading}
      />
      <select value={category} onChange={(e) => setCategory(e.target.value)} disabled={loading}>
        <option value="coding">Coding</option>
        <option value="research">Research</option>
      </select>
      <div className="form-actions">
        <button type="submit" disabled={loading || !taskText.trim()}>
          {loading ? 'Running...' : 'Run Task'}
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}
      {activeTaskId && (
        <p className="current-task">Active: {activeTaskId}</p>
      )}
    </form>
  );
}
