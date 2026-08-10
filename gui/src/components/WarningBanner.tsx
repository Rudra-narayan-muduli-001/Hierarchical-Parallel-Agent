import { useTreeStore } from '../state/treeStore';
import { AlertIcon, CloseIcon } from './icons';

const KIND_LABEL: Record<string, string> = {
  failure_threshold: 'Failure threshold reached',
  degraded: 'Degraded hierarchy',
};

export function WarningBanner() {
  const { warnings, dismissWarning } = useTreeStore();

  if (!warnings || warnings.length === 0) return null;

  return (
    <div className="panel">
      <div className="panel-title"><AlertIcon size={13} /> Notices</div>
      <div className="warning-banner">
        {warnings.map((w: any, i: number) => (
          <div key={i} className={`warning-item ${w.kind || 'generic'}`}>
            <AlertIcon size={13} />
            <div>
              <strong>{KIND_LABEL[w.kind] || 'Notice'}</strong>
              <div style={{ marginTop: 2 }}>{w.message || ''}</div>
            </div>
            <button className="warning-dismiss" onClick={() => dismissWarning(i)} title="Dismiss">
              <CloseIcon size={12} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
