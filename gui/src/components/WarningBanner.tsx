import { useTreeStore } from '../state/treeStore';

export function WarningBanner() {
  const { warnings } = useTreeStore();

  if (warnings.length === 0) return null;

  return (
    <div className="warning-banner">
      {warnings.map((w: any, i: number) => (
        <div key={i} className={`warning ${w.kind}`}>
          <span className="warning-icon">⚠</span>
          <span>{w.message}</span>
        </div>
      ))}
    </div>
  );
}
