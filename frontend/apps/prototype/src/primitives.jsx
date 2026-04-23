// Shared primitive components
const { useState, useEffect, useRef, useCallback } = React;

function Spinner({ size = 14, color = 'var(--accent)' }) {
  return (
    <span style={{
      display: 'inline-block', width: size, height: size,
      border: `2px solid color-mix(in oklch, ${color} 20%, transparent)`,
      borderTopColor: color,
      borderRadius: '50%',
      animation: 'spin 0.7s linear infinite',
      flexShrink: 0,
    }} />
  );
}

function Badge({ variant = 'neutral', children }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

function Btn({ variant = 'secondary', size, icon, children, ...props }) {
  return (
    <button className={`btn btn-${variant}${size ? ' btn-' + size : ''}${!children ? ' btn-icon' : ''}`} {...props}>
      {icon && <span style={{ display: 'flex', alignItems: 'center' }}>{icon}</span>}
      {children}
    </button>
  );
}

function Toggle({ label, sublabel, checked, onChange }) {
  return (
    <div className="toggle-wrap">
      <div>
        <div style={{ fontSize: 13, fontWeight: 500 }}>{label}</div>
        {sublabel && <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 1 }}>{sublabel}</div>}
      </div>
      <label className="toggle">
        <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
        <span className="toggle-slider" />
      </label>
    </div>
  );
}

function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs">
      {tabs.map(t => (
        <button key={t.id} className={`tab-btn${active === t.id ? ' active' : ''}`} onClick={() => onChange(t.id)}>
          {t.label}
          {t.count != null && (
            <span style={{ marginLeft: 5, fontSize: 11, background: 'var(--surface-raised)', borderRadius: 100, padding: '1px 5px', color: 'var(--text-muted)' }}>
              {t.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

function Toast({ toasts }) {
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type}`}>
          <span>{t.type === 'success' ? '✓' : '✕'}</span>
          {t.msg}
        </div>
      ))}
    </div>
  );
}

function useToasts() {
  const [toasts, setToasts] = useState([]);
  const add = useCallback((msg, type = 'success') => {
    const id = Date.now();
    setToasts(p => [...p, { id, msg, type }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3000);
  }, []);
  return [toasts, add];
}

function Dialog({ title, children, footer, onClose }) {
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);
  return (
    <div className="dialog-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="dialog" role="dialog" aria-modal="true" aria-label={title}>
        <div className="dialog-header">
          <span className="dialog-title">{title}</span>
          <Btn variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </Btn>
        </div>
        <div className="dialog-body">{children}</div>
        {footer && <div className="dialog-footer">{footer}</div>}
      </div>
    </div>
  );
}

// Icon components
const Icons = {
  ChevronRight: () => (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  Copy: () => (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
      <rect x="4" y="4" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M3 9H2a1 1 0 01-1-1V2a1 1 0 011-1h6a1 1 0 011 1v1" stroke="currentColor" strokeWidth="1.3"/>
    </svg>
  ),
  ExternalLink: () => (
    <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
      <path d="M6.5 1.5H9.5V4.5M9.5 1.5L5 6M1.5 3.5h3m-3 4h6v-3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  Plus: () => (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
      <path d="M6.5 1.5v10M1.5 6.5h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  Trash: () => (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
      <path d="M1.5 3.5h10M4.5 3.5V2h4v1.5M5.5 6v4.5M7.5 6v4.5M2.5 3.5l.5 7a1 1 0 001 1h5a1 1 0 001-1l.5-7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  Search: () => (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M9.5 9.5l3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    </svg>
  ),
  Edit: () => (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
      <path d="M8.5 2l2.5 2.5-7 7H1.5V9l7-7z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  Check: () => (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
      <path d="M2 6.5l3.5 3.5 5.5-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
};

Object.assign(window, { Spinner, Badge, Btn, Toggle, Tabs, Toast, Dialog, Icons, useToasts });
