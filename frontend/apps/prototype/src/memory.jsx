// Memory page — PreferencesTable, DomainListEditor, SemanticSearchPanel
const { useState: useStateM, useRef: useRefM, useEffect: useEffectM } = React;

function MemoryPage() {
  const [toasts, addToast] = useToasts();
  const [activeTab, setActiveTab] = useStateM('preferences');

  const tabs = [
    { id: 'preferences', label: 'Preferences' },
    { id: 'domains',     label: 'Domain Lists' },
    { id: 'search',      label: 'Semantic Search' },
  ];

  return (
    <div className="memory-page">
      <div className="memory-inner">
        <div style={{ marginBottom: 28 }}>
          <h1 className="memory-heading">Memory & Preferences</h1>
          <p className="memory-sub">
            Manage persistent preferences, domain allow/deny lists, and search past research.
            Deny-list takes precedence over allow-list.
          </p>
          <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
        </div>

        {activeTab === 'preferences' && <PreferencesPanel addToast={addToast} />}
        {activeTab === 'domains'     && <DomainsPanel addToast={addToast} />}
        {activeTab === 'search'      && <SemanticSearchPanel />}
      </div>
      <Toast toasts={toasts} />
    </div>
  );
}

// ─── Preferences ─────────────────────────────────────────────────────────────
function PreferencesPanel({ addToast }) {
  const [prefs, setPrefs] = useStateM([...MOCK_PREFERENCES]);
  const [editingKey, setEditingKey] = useStateM(null);
  const [editVal, setEditVal] = useStateM('');
  const [newKey, setNewKey] = useStateM('');
  const [newVal, setNewVal] = useStateM('');
  const [adding, setAdding] = useStateM(false);

  const startEdit = (p) => { setEditingKey(p.key); setEditVal(p.value); };
  const saveEdit = (key) => {
    setPrefs(p => p.map(pf => pf.key === key ? { ...pf, value: editVal, updatedAt: new Date().toISOString().slice(0,10), source: 'user' } : pf));
    setEditingKey(null);
    addToast('Preference saved', 'success');
  };
  const del = (key) => {
    setPrefs(p => p.filter(pf => pf.key !== key));
    addToast('Preference deleted', 'success');
  };
  const addPref = () => {
    if (!newKey.trim() || !newVal.trim()) return;
    if (prefs.find(p => p.key === newKey.trim())) { addToast('Key already exists', 'error'); return; }
    setPrefs(p => [...p, { key: newKey.trim(), value: newVal.trim(), source: 'user', updatedAt: new Date().toISOString().slice(0,10) }]);
    setNewKey(''); setNewVal(''); setAdding(false);
    addToast('Preference added', 'success');
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {prefs.length} preferences
        </div>
        <Btn variant="secondary" size="sm" icon={<Icons.Plus />}
          onClick={() => setAdding(p => !p)} data-testid="preference-save">
          Add
        </Btn>
      </div>

      {adding && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--accent-subtle)', borderRadius: 'var(--r-lg)', padding: 14, marginBottom: 14, display: 'flex', gap: 8, alignItems: 'center', animation: 'fadeIn 0.15s ease' }}>
          <input type="text" placeholder="key" value={newKey} onChange={e => setNewKey(e.target.value)}
            style={{ flex: 1, padding: '7px 10px', fontSize: 13, fontFamily: 'var(--font-mono)' }} />
          <input type="text" placeholder="value" value={newVal} onChange={e => setNewVal(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addPref()}
            style={{ flex: 2, padding: '7px 10px', fontSize: 13 }} />
          <Btn variant="primary" size="sm" onClick={addPref} icon={<Icons.Check />}>Save</Btn>
          <Btn variant="ghost" size="sm" onClick={() => setAdding(false)}>Cancel</Btn>
        </div>
      )}

      <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
        <table className="pref-table">
          <thead>
            <tr>
              <th>Key</th>
              <th>Value</th>
              <th>Source</th>
              <th>Updated</th>
              <th style={{ width: 80 }}></th>
            </tr>
          </thead>
          <tbody>
            {prefs.map(p => (
              <tr key={p.key}>
                <td className="pref-key">{p.key}</td>
                <td>
                  {editingKey === p.key
                    ? <div style={{ display: 'flex', gap: 6 }}>
                        <input type="text" value={editVal} onChange={e => setEditVal(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') saveEdit(p.key); if (e.key === 'Escape') setEditingKey(null); }}
                          autoFocus
                          style={{ flex: 1, padding: '4px 8px', fontSize: 13, borderRadius: 'var(--r-sm)' }} />
                        <Btn variant="primary" size="sm" onClick={() => saveEdit(p.key)}><Icons.Check /></Btn>
                      </div>
                    : <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5, color: 'var(--text)' }}>{p.value}</span>
                  }
                </td>
                <td>
                  <span className="pref-source" style={{ color: p.source === 'inferred' ? 'var(--unverified)' : 'var(--text-muted)' }}>
                    {p.source === 'inferred' ? '◈ inferred' : '● user'}
                  </span>
                </td>
                <td><span style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, color: 'var(--text-dim)' }}>{p.updatedAt}</span></td>
                <td>
                  <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                    <Btn variant="ghost" size="sm" onClick={() => startEdit(p)} aria-label={`Edit ${p.key}`}><Icons.Edit /></Btn>
                    <Btn variant="ghost" size="sm" onClick={() => del(p.key)} aria-label={`Delete ${p.key}`}
                      style={{ color: 'var(--blocked)' }}><Icons.Trash /></Btn>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
        <span style={{ color: 'var(--unverified)' }}>◈ inferred</span> = derived from usage patterns · <span>● user</span> = explicitly set
      </div>
    </div>
  );
}

// ─── Domain Lists ──────────────────────────────────────────────────────────
function DomainsPanel({ addToast }) {
  const [allow, setAllow] = useStateM([...MOCK_ALLOW_DOMAINS]);
  const [deny,  setDeny]  = useStateM([...MOCK_DENY_DOMAINS]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
      <DomainList
        label="Allow Domains"
        sublabel="Sources in this list are preferred. Leave empty to allow all."
        variant="verified"
        domains={allow}
        setDomains={setAllow}
        addToast={addToast}
        emptyMsg="No domain preferences — all sources allowed"
      />
      <DomainList
        label="Deny Domains"
        sublabel="Sources in this list are never used. Deny wins over allow."
        variant="blocked"
        domains={deny}
        setDomains={setDeny}
        addToast={addToast}
        emptyMsg="No domains blocked"
      />
    </div>
  );
}

function DomainList({ label, sublabel, variant, domains, setDomains, addToast, emptyMsg }) {
  const [input, setInput] = useStateM('');
  const accentColor = variant === 'verified' ? 'var(--verified)' : 'var(--blocked)';
  const bgColor     = variant === 'verified' ? 'var(--verified-bg)' : 'var(--blocked-bg)';

  const add = () => {
    const v = input.trim().replace(/^https?:\/\//, '').split('/')[0];
    if (!v) return;
    // Basic hostname validation
    if (!/^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(v)) { addToast('Invalid hostname pattern', 'error'); return; }
    if (domains.includes(v)) { addToast('Already in list', 'error'); return; }
    setDomains(p => [...p, v]);
    setInput('');
    addToast(`Added to ${label.toLowerCase()}`, 'success');
  };

  return (
    <div>
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: accentColor, marginBottom: 3 }}>{label}</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sublabel}</div>
      </div>
      <div style={{ display: 'flex', gap: 7, marginBottom: 12 }}>
        <input type="text" value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(); }}}
          placeholder="e.g. nature.com"
          data-testid="domain-list-add"
          style={{ flex: 1, padding: '7px 10px', fontSize: 13 }} />
        <Btn variant="secondary" size="sm" icon={<Icons.Plus />} onClick={add}>Add</Btn>
      </div>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--r-lg)', padding: 12, minHeight: 80 }}>
        {domains.length === 0
          ? <div style={{ fontSize: 12.5, color: 'var(--text-dim)', textAlign: 'center', padding: '16px 0' }}>{emptyMsg}</div>
          : domains.map(d => (
            <div key={d} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '5px 8px', borderRadius: 'var(--r-sm)', background: bgColor, marginBottom: 5 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5, color: accentColor }}>{d}</span>
              <button onClick={() => { setDomains(p => p.filter(x => x !== d)); addToast('Removed', 'success'); }}
                style={{ background: 'none', border: 'none', color: accentColor, cursor: 'pointer', fontSize: 14, padding: '0 2px', opacity: 0.7, lineHeight: 1 }}
                aria-label={`Remove ${d}`}>×</button>
            </div>
          ))
        }
      </div>
    </div>
  );
}

// ─── Semantic Search ──────────────────────────────────────────────────────────
function SemanticSearchPanel() {
  const [query, setQuery] = useStateM('');
  const [results, setResults] = useStateM(null);
  const [loading, setLoading] = useStateM(false);

  const search = () => {
    if (!query.trim()) return;
    setLoading(true);
    setTimeout(() => {
      setResults(MOCK_SEMANTIC_RESULTS.filter(r =>
        r.title.toLowerCase().includes(query.toLowerCase()) ||
        r.snippet.toLowerCase().includes(query.toLowerCase()) ||
        query.toLowerCase().split(' ').some(w => r.title.toLowerCase().includes(w) || r.snippet.toLowerCase().includes(w))
      ).length > 0
        ? MOCK_SEMANTIC_RESULTS
        : []
      );
      setLoading(false);
    }, 600);
  };

  return (
    <div className="search-panel">
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 5 }}>Search Past Research</div>
        <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginBottom: 14 }}>
          Semantic search over reports and preference embeddings stored in Chroma.
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <input
              type="search"
              className="search-input"
              placeholder="e.g. attention mechanisms, scaling laws, emergent behavior…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && search()}
            />
          </div>
          <Btn variant="primary" onClick={search} disabled={loading || !query.trim()}
            icon={loading ? <Spinner size={13} color="#fff" /> : <Icons.Search />}>
            {loading ? 'Searching…' : 'Search'}
          </Btn>
        </div>
      </div>

      {results === null && (
        <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-dim)' }}>
          <div style={{ fontSize: 28, marginBottom: 8, opacity: 0.3 }}>◈</div>
          <div style={{ fontSize: 13 }}>Search your research memory</div>
          <div style={{ fontSize: 12, marginTop: 4, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            GET /memory/search?q=…
          </div>
        </div>
      )}

      {results !== null && results.length === 0 && (
        <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-dim)', fontSize: 13 }}>
          No results found for "{query}"
        </div>
      )}

      {results && results.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginBottom: 10 }}>
            {results.length} results · ranked by semantic similarity
          </div>
          {results.map(r => (
            <div key={r.id} className="search-result">
              <div className="search-result-title">{r.title}</div>
              <div className="search-result-snippet">{r.snippet}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
                <span className="search-score">score: {r.score.toFixed(2)}</span>
                <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{r.date}</span>
                <div style={{ marginLeft: 'auto', height: 4, width: 60, background: 'var(--surface-raised)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${r.score * 100}%`, background: 'var(--accent)', borderRadius: 2 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { MemoryPage });
