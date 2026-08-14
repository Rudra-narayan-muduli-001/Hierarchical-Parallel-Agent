import { useEffect, useRef, useState } from 'react';
import { useTreeStore } from '../state/treeStore';
import { SendIcon, StopIcon, AlertIcon } from './icons';
import { fetchConfig } from '../api/rest';

export function ChatComposer() {
  const { submitTask, activeTaskId, loading } = useTreeStore();
  const [text, setText] = useState('');
  const [category, setCategory] = useState('coding');
  const [categories, setCategories] = useState<string[]>(['coding', 'research']);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetchConfig()
      .then((cfg) => {
        if (Array.isArray(cfg.categories) && cfg.categories.length > 0) {
          setCategories(cfg.categories);
          if (!cfg.categories.includes(category)) setCategory(cfg.categories[0]);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
    }
  }, [text]);

  const submit = async () => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    setError(null);
    setText('');
    try {
      await submitTask(trimmed, category);
      // Keep focus for rapid follow-ups
      textareaRef.current?.focus();
    } catch (err: any) {
      setError(err.message || 'Submission failed');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="composer">
      {error && (
        <div className="composer-error">
          <AlertIcon size={14} />
          <span>{error}</span>
        </div>
      )}
      <div className="composer-box">
        <div className="composer-stack">
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            placeholder="Message Parallel Mind…  (Shift+Enter for newline)"
            value={text}
            rows={1}
            disabled={loading}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className="composer-tools">
            <div className="category-picker">
              {categories.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`cat-pill ${category === c ? 'cat-pill-active' : ''}`}
                  onClick={() => setCategory(c)}
                  title={`ask as ${c}`}
                >
                  {c}
                </button>
              ))}
            </div>
            <div className="composer-hint">
              {activeTaskId ? `running: ${activeTaskId}` : 'enter to send · shift+enter for newline'}
            </div>
          </div>
        </div>
        <button
          className="send-btn"
          onClick={submit}
          disabled={loading || !text.trim()}
          title="Run task"
        >
          {loading ? <StopIcon size={18} /> : <SendIcon size={18} />}
        </button>
      </div>
    </div>
  );
}
