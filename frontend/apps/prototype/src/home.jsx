// Home page — TopicForm + AdvancedOptions
const { useState: useStateH, useRef: useRefH } = React;

function HomePage({ navigate }) {
  const [topic, setTopic] = useStateH('');
  const [open, setOpen] = useStateH(false);
  const [depth, setDepth] = useStateH(1); // 0=quick,1=standard,2=deep
  const [tools, setTools] = useStateH({ web: true, arxiv: true, pdf: true, url: false, code: false });
  const [domainInput, setDomainInput] = useStateH('');
  const [domains, setDomains] = useStateH([]);
  const [submitting, setSubmitting] = useStateH(false);
  const textareaRef = useRefH(null);

  const depthLabels = ['Quick', 'Standard', 'Deep'];
  const depthDescs  = ['~30s · 3–5 sources', '~90s · 8–12 sources', '~3min · 20+ sources'];

  const addDomain = () => {
    const v = domainInput.trim().replace(/^https?:\/\//, '').split('/')[0];
    if (v && !domains.includes(v)) setDomains(p => [...p, v]);
    setDomainInput('');
  };

  const submit = () => {
    if (!topic.trim()) { textareaRef.current?.focus(); return; }
    setSubmitting(true);
    setTimeout(() => { navigate('/reports/demo'); }, 600);
  };

  return (
    <div className="home-page">
      <div className="home-inner">
        {/* Header */}
        <div style={{ marginBottom: 48 }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            background: 'var(--accent-bg)', border: '1px solid var(--accent-subtle)',
            borderRadius: 100, padding: '4px 12px', marginBottom: 20,
            fontSize: 12, color: 'var(--accent)', fontFamily: 'var(--font-mono)',
            fontWeight: 500,
          }}>
            <span className="status-dot" style={{ width: 5, height: 5 }} />
            AetherMind Research Agent · v2.1
          </div>
          <h1 className="home-heading">What would you<br />like to research?</h1>
          <p className="home-sub">
            Formulate a research question or topic. The agent will plan sub-questions,
            search across sources, synthesize a structured report, and verify citations.
          </p>
        </div>

        {/* Topic input */}
        <div className="topic-form">
          <textarea
            ref={textareaRef}
            className="topic-textarea"
            placeholder="e.g. How do transformer attention mechanisms give rise to emergent capabilities in large language models?"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(); }}
            data-testid="topic-input"
          />
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              ⌘↵ to submit
            </span>
            <Btn
              variant="primary"
              size="lg"
              onClick={submit}
              disabled={submitting || !topic.trim()}
              data-testid="submit-research"
              icon={submitting ? <Spinner size={15} color="#fff" /> : null}
            >
              {submitting ? 'Starting…' : 'Start Research'}
            </Btn>
          </div>
        </div>

        {/* Advanced options */}
        <div className="adv-options">
          <button
            className={`adv-toggle-btn${open ? ' open' : ''}`}
            onClick={() => setOpen(p => !p)}
            aria-expanded={open}
          >
            <Icons.ChevronRight />
            Advanced options
            <span style={{ fontSize: 11, color: 'var(--text-dim)', marginLeft: 4, fontFamily: 'var(--font-mono)' }}>
              {depthLabels[depth]} · {Object.values(tools).filter(Boolean).length} tools
            </span>
          </button>

          {open && (
            <div className="adv-panel">
              {/* Depth */}
              <div>
                <div className="adv-section-label">Research Depth</div>
                <input
                  type="range" min={0} max={2} step={1}
                  value={depth}
                  onChange={e => setDepth(+e.target.value)}
                  className="depth-slider"
                  aria-label="Research depth"
                />
                <div className="depth-labels">
                  {depthLabels.map((l, i) => (
                    <span key={l} style={{ color: depth === i ? 'var(--accent)' : undefined, fontWeight: depth === i ? 600 : 400 }}>
                      {l}
                    </span>
                  ))}
                </div>
                <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {depthDescs[depth]}
                </div>
              </div>

              {/* Tools */}
              <div>
                <div className="adv-section-label">Source Tools</div>
                <div className="tools-grid">
                  {[
                    { key: 'web',   label: 'Web Search',   sub: 'General web results' },
                    { key: 'arxiv', label: 'arXiv',        sub: 'Academic preprints' },
                    { key: 'pdf',   label: 'PDF Fetch',    sub: 'Full-text extraction' },
                    { key: 'url',   label: 'URL Fetch',    sub: 'Specific pages' },
                    { key: 'code',  label: 'Code Exec',    sub: 'Calculations & analysis' },
                  ].map(t => (
                    <Toggle
                      key={t.key}
                      label={t.label}
                      sublabel={t.sub}
                      checked={tools[t.key]}
                      onChange={v => setTools(p => ({ ...p, [t.key]: v }))}
                    />
                  ))}
                </div>
              </div>

              {/* Domain hints */}
              <div>
                <div className="adv-section-label">Preferred Domains <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>(optional hints)</span></div>
                <div className="domain-input-wrap">
                  <input
                    type="text"
                    value={domainInput}
                    onChange={e => setDomainInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addDomain(); } }}
                    placeholder="e.g. nature.com"
                    style={{ flex: 1, padding: '7px 11px', fontSize: 13 }}
                    aria-label="Add preferred domain"
                  />
                  <Btn variant="secondary" size="sm" onClick={addDomain} icon={<Icons.Plus />}>Add</Btn>
                </div>
                {domains.length > 0 && (
                  <div className="domain-tags">
                    {domains.map(d => (
                      <span key={d} className="domain-tag">
                        {d}
                        <button className="domain-tag-rm" onClick={() => setDomains(p => p.filter(x => x !== d))} aria-label={`Remove ${d}`}>×</button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Recent research */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginBottom: 12 }}>
            Recent
          </div>
          {[
            { id: 'demo', title: 'Transformer Attention Mechanisms and Emergent Capabilities', date: 'Today', depth: 'Deep' },
            { id: 'x2',   title: 'Mechanistic Interpretability in Sparse Autoencoders',       date: 'Apr 18', depth: 'Standard' },
            { id: 'x3',   title: 'Phase Transitions in Neural Network Generalization',         date: 'Apr 14', depth: 'Quick' },
          ].map(r => (
            <div
              key={r.id}
              onClick={() => navigate('/reports/' + r.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '11px 14px', borderRadius: 'var(--r)',
                border: '1px solid var(--border-subtle)',
                marginBottom: 6, cursor: 'pointer',
                transition: 'border-color 0.15s, background 0.15s',
                background: 'var(--surface)',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--surface-raised)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.background = 'var(--surface)'; }}
            >
              <div style={{ width: 32, height: 32, borderRadius: 'var(--r-sm)', background: 'var(--accent-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="1.5" y="1.5" width="11" height="11" rx="2" stroke="var(--accent)" strokeWidth="1.2"/>
                  <path d="M4 5h6M4 7h4M4 9h5" stroke="var(--accent)" strokeWidth="1.2" strokeLinecap="round"/>
                </svg>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.title}</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>{r.date} · {r.depth}</div>
              </div>
              <Icons.ChevronRight />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { HomePage });
