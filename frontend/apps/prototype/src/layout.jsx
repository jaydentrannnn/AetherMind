// Layout: AppShell + TopNav
const { useState: useStateL } = React;

function TopNav({ route, navigate }) {
  return (
    <nav className="topnav">
      <div className="topnav-logo" onClick={() => navigate('/')} role="button" tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && navigate('/')}>
        <div className="logo-mark">Æ</div>
        <span className="logo-text">AetherMind</span>
      </div>
      <div className="topnav-links">
        <button
          className={`nav-link${route === '/' ? ' active' : ''}`}
          onClick={() => navigate('/')}
        >Research</button>
        <button
          className={`nav-link${route === '/memory' ? ' active' : ''}`}
          onClick={() => navigate('/memory')}
        >Memory</button>
        {route.startsWith('/reports/') && (
          <button className="nav-link active" disabled style={{ opacity: 1 }}>
            Report
          </button>
        )}
      </div>
      <div className="topnav-right">
        <div className="nav-status">
          <span className="status-dot" />
          API connected
        </div>
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: 'var(--accent-bg)',
          border: '1px solid var(--accent-subtle)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 600, color: 'var(--accent)',
          cursor: 'pointer',
        }} title="Account">JD</div>
      </div>
    </nav>
  );
}

function AppShell({ route, navigate, children }) {
  return (
    <div className="app-shell">
      <TopNav route={route} navigate={navigate} />
      <div className="app-main">
        {children}
      </div>
    </div>
  );
}

Object.assign(window, { AppShell, TopNav });
