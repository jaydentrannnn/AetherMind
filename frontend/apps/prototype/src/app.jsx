// App root + hash router
const { useState: useStateApp, useEffect: useEffectApp } = React;

function App() {
  const getRoute = () => {
    const h = window.location.hash.replace('#', '') || '/';
    return h;
  };

  const [route, setRoute] = useStateApp(getRoute);

  useEffectApp(() => {
    const onHash = () => setRoute(getRoute());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const navigate = (path) => {
    window.location.hash = path;
    setRoute(path);
  };

  // Restore last route from localStorage
  useEffectApp(() => {
    const saved = localStorage.getItem('aethermind-last-route');
    if (saved && saved !== '/' && window.location.hash === '') {
      navigate(saved);
    }
  }, []);

  useEffectApp(() => {
    localStorage.setItem('aethermind-last-route', route);
  }, [route]);

  const renderPage = () => {
    if (route === '/') return <HomePage navigate={navigate} />;
    if (route === '/memory') return <MemoryPage />;
    if (route.startsWith('/reports/')) {
      const id = route.replace('/reports/', '');
      return <ReportPage jobId={id} navigate={navigate} />;
    }
    // 404
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
        <div style={{ fontSize: 48, opacity: 0.15, fontFamily: 'var(--font-serif)' }}>404</div>
        <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Page not found</div>
        <Btn variant="secondary" onClick={() => navigate('/')}>Back to Home</Btn>
      </div>
    );
  };

  return (
    <AppShell route={route} navigate={navigate}>
      {renderPage()}
    </AppShell>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
