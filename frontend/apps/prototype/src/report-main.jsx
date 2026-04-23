// Report main area — MarkdownReport, CitationPopover, Tabs (Sources / Guardrails / Rubric / Versions)
const { useState: useStateR, useRef: useRefR, useEffect: useEffectR, useCallback: useCbR } = React;

// ─── Citation Popover ───────────────────────────────────────────────────────
function CitationChip({ sourceId, sources, idx }) {
  const [open, setOpen] = useStateR(false);
  const ref = useRefR(null);
  const src = sources.find(s => s.id === sourceId);

  useEffectR(() => {
    if (!open) return;
    const close = e => { if (!ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  const chipClass = `cite-chip${src?.verified === false ? ' unverified' : src?.verified ? ' verified' : ''}`;

  return (
    <span ref={ref} style={{ position: 'relative', display: 'inline' }}>
      <span
        className={chipClass}
        tabIndex={0}
        role="button"
        aria-label={`Citation ${idx}${src ? ': ' + src.title : ''}`}
        data-testid="open-citation-popover"
        onClick={() => setOpen(p => !p)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(p => !p); }}}
      >
        {idx}
      </span>
      {open && src && (
        <div className="popover" style={{ bottom: '130%', left: '50%', transform: 'translateX(-50%)' }} role="tooltip">
          <div className="popover-title">{src.title}</div>
          <div className="popover-url">{src.url}</div>
          {src.snippet && <div className="popover-snippet">"{src.snippet}"</div>}
          <div className="popover-footer">
            <Badge variant={src.verified ? 'verified' : 'unverified'}>
              {src.verified ? '✓ Verified' : '⚠ Unverified'}
            </Badge>
            <a href={src.url} target="_blank" rel="noopener noreferrer"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>
              Open <Icons.ExternalLink />
            </a>
          </div>
        </div>
      )}
      {open && !src && (
        <div className="popover" style={{ bottom: '130%', left: 0 }}>
          <span style={{ color: 'var(--blocked)', fontSize: 12 }}>⚠ Source not found</span>
        </div>
      )}
    </span>
  );
}

// Build source index: source_id → display number
function buildSourceIndex(report) {
  const idx = {};
  let n = 1;
  report.sections.forEach(sec =>
    sec.content.forEach(block => {
      if (block.citations) block.citations.forEach(id => {
        if (!idx[id]) idx[id] = n++;
      });
    })
  );
  return idx;
}

// ─── Report Content ─────────────────────────────────────────────────────────
function ReportContent({ report, loading }) {
  const sourceIdx = buildSourceIndex(report);

  if (loading) return (
    <div style={{ padding: '40px 32px', maxWidth: 740, margin: '0 auto' }}>
      {[280, 180, 320, 240, 200].map((w, i) => (
        <div key={i} className="skeleton" style={{ height: 16, width: `${w}px`, marginBottom: 14, maxWidth: '100%' }} />
      ))}
    </div>
  );

  return (
    <div className="report-content">
      <h1 className="report-title">{report.title}</h1>

      {/* Meta */}
      <div className="report-meta">
        <Badge variant="neutral" style={{ fontFamily: 'var(--font-mono)' }}>
          {new Date(report.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </Badge>
        <Badge variant="accent">{report.depth}</Badge>
        <Badge variant="neutral">{report.sources.length} sources</Badge>
        <Badge variant="verified">
          {report.sources.filter(s => s.verified).length}/{report.sources.length} verified
        </Badge>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)', marginLeft: 4 }}>
          #{report.id}
        </span>
      </div>

      {/* Summary */}
      <div className="report-summary">{report.summary}</div>

      {/* Sections */}
      {report.sections.map(sec => (
        <div key={sec.id} className="report-section">
          <h2>{sec.title}</h2>
          {sec.content.map((block, bi) => (
            <ReportBlock key={bi} block={block} sources={report.sources} sourceIdx={sourceIdx} />
          ))}
        </div>
      ))}

      {/* Footnotes */}
      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 24, marginTop: 8 }}>
        <div style={{ fontSize: 11.5, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginBottom: 12 }}>
          References
        </div>
        {Object.entries(sourceIdx).map(([sid, num]) => {
          const src = report.sources.find(s => s.id === sid);
          if (!src) return null;
          return (
            <div key={sid} style={{ display: 'flex', gap: 10, marginBottom: 7, alignItems: 'flex-start' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)', width: 20, flexShrink: 0, paddingTop: 1 }}>[{num}]</span>
              <div>
                <a href={src.url} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 13, color: 'var(--accent)', textDecoration: 'none', fontFamily: 'var(--font-serif)' }}>
                  {src.title}
                </a>
                <div style={{ fontSize: 11.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
                  {src.domain} · {src.type}
                  {!src.verified && <span style={{ color: 'var(--unverified)', marginLeft: 6 }}>⚠ unverified</span>}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ReportBlock({ block, sources, sourceIdx }) {
  const renderWithCitations = (text, cites) => {
    if (!cites || cites.length === 0) return text;
    return (
      <>
        {text}
        {cites.map(sid => (
          <CitationChip key={sid} sourceId={sid} sources={sources} idx={sourceIdx[sid] || '?'} />
        ))}
      </>
    );
  };

  if (block.type === 'p') {
    return <p>{renderWithCitations(block.text, block.citations)}</p>;
  }
  if (block.type === 'table') {
    return (
      <div style={{ overflowX: 'auto', marginBottom: 16 }}>
        <table>
          <thead><tr>{block.headers.map(h => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {block.rows.map((row, i) => (
              <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return null;
}

// ─── Sources Tab ─────────────────────────────────────────────────────────────
function SourcesTab({ sources }) {
  return (
    <div className="sources-list">
      {sources.map(src => (
        <div key={src.id} className="source-item">
          <div className="source-title">{src.title}</div>
          <div className="source-url">{src.url}</div>
          <div className="source-meta">
            <Badge variant={src.verified ? 'verified' : 'unverified'}>
              {src.verified ? '✓ Verified' : '⚠ Unverified'}
            </Badge>
            <Badge variant="neutral">{src.type}</Badge>
            <span style={{ fontSize: 11.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{src.domain}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Guardrails Tab ─────────────────────────────────────────────────────────
function GuardrailsTab({ guardrails }) {
  const { unverified_claims, policy_violations, closure_violations } = guardrails;
  return (
    <div style={{ padding: 16 }}>
      <Section label="Unverified Claims" count={unverified_claims.length} color="var(--unverified)">
        {unverified_claims.length === 0
          ? <EmptyItem label="All claims verified" />
          : unverified_claims.map((g, i) => (
            <div key={i} className="guardrail-item unverified">
              <div className="guardrail-claim">{g.claim}</div>
              <div className="guardrail-rationale">{g.rationale}</div>
            </div>
          ))}
      </Section>
      <Section label="Policy Violations" count={policy_violations.length} color="var(--blocked)">
        {policy_violations.length === 0
          ? <EmptyItem label="No policy violations" />
          : policy_violations.map((g, i) => (
            <div key={i} className="guardrail-item blocked">
              <div className="guardrail-claim">{g.claim}</div>
              <div className="guardrail-rationale">{g.rationale}</div>
            </div>
          ))}
      </Section>
      <Section label="Closure Violations" count={closure_violations.length} color="var(--unverified)">
        {closure_violations.length === 0
          ? <EmptyItem label="No closure violations" />
          : closure_violations.map((g, i) => (
            <div key={i} className="guardrail-item unverified">
              <div className="guardrail-claim">{g.claim}</div>
              <div className="guardrail-rationale">{g.rationale}</div>
            </div>
          ))}
      </Section>
    </div>
  );
}

function Section({ label, count, color, children }) {
  const [open, setOpen] = useStateR(true);
  return (
    <div style={{ marginBottom: 20 }}>
      <button onClick={() => setOpen(p => !p)} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, width: '100%', textAlign: 'left' }}>
        <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{label}</span>
        <span style={{ fontSize: 11, background: 'var(--surface-raised)', borderRadius: 100, padding: '1px 7px', color }}>{count}</span>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-dim)' }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && children}
    </div>
  );
}

function EmptyItem({ label }) {
  return (
    <div className="guardrail-item ok">
      <div style={{ fontSize: 13, color: 'var(--verified)', display: 'flex', alignItems: 'center', gap: 6 }}>
        <Icons.Check /> {label}
      </div>
    </div>
  );
}

// ─── Rubric Tab ───────────────────────────────────────────────────────────
function RubricTab({ rubric }) {
  return (
    <div style={{ padding: 16 }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 12 }}>Critic Evaluation</div>
      {Object.values(rubric).map(r => (
        <div key={r.label} className="rubric-row">
          <span className="rubric-label">{r.label}</span>
          <div className="rubric-bar">
            <div className="rubric-fill" style={{ width: `${(r.score / r.max) * 100}%`, background: r.score >= 4 ? 'var(--verified)' : r.score >= 3 ? 'var(--unverified)' : 'var(--blocked)' }} />
          </div>
          <span className="rubric-score">{r.score}/{r.max}</span>
        </div>
      ))}
      <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--surface-raised)', borderRadius: 'var(--r)', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>
        Overall: <strong style={{ color: 'var(--text)' }}>4.4 / 5.0</strong>
        <span style={{ marginLeft: 12, color: 'var(--verified)' }}>Accepted for finalization</span>
      </div>
    </div>
  );
}

// ─── Version Diff ────────────────────────────────────────────────────────────
function VersionsTab({ versions }) {
  const [selA, setSelA] = useStateR('v2');
  const [selB, setSelB] = useStateR('v3');

  const v = (id) => versions.find(v => v.id === id);
  const diffLines = [
    { type: 'ctx',    text: '  …scaling laws predict smooth performance improvements across model sizes.' },
    { type: 'remove', text: '- Emergent abilities are absent at smaller scales and appear sharply at exactly 100B parameters.' },
    { type: 'add',    text: '+ Emergent abilities, as defined by Wei et al. (2022), are absent at smaller scales and' },
    { type: 'add',    text: '+   appear approximately at scales beyond 50–100B parameters, though thresholds vary by task.' },
    { type: 'ctx',    text: '  However, Schaeffer et al. (2023) argue that emergence may be an artifact…' },
    { type: 'ctx',    text: '' },
    { type: 'remove', text: '- The safety implications are clear and well-understood.' },
    { type: 'add',    text: '+ From a safety perspective, emergent capabilities imply that scale-based risk assessments' },
    { type: 'add',    text: '+   may be unreliable if capabilities appear discontinuously.' },
  ];

  return (
    <div style={{ padding: 16 }}>
      {/* Version selector */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>From</span>
          <select value={selA} onChange={e => setSelA(e.target.value)}
            style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r)', padding: '5px 8px', fontSize: 12, flex: 1 }}>
            {versions.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}
          </select>
        </div>
        <span style={{ color: 'var(--text-dim)', fontSize: 14 }}>→</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>To</span>
          <select value={selB} onChange={e => setSelB(e.target.value)}
            style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', borderRadius: 'var(--r)', padding: '5px 8px', fontSize: 12, flex: 1 }}>
            {versions.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}
          </select>
        </div>
      </div>

      {selA === selB ? (
        <div className="empty-state"><div className="empty-msg">Select two different versions to compare</div></div>
      ) : (
        <>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>{v(selB)?.summary_diff}</div>
          </div>
          <div style={{ background: 'var(--bg)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--r)', overflow: 'hidden' }}>
            <div style={{ padding: '6px 12px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface)', fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', display: 'flex', gap: 16 }}>
              <span style={{ color: 'var(--blocked)' }}>― {v(selA)?.label}</span>
              <span style={{ color: 'var(--verified)' }}>+ {v(selB)?.label}</span>
            </div>
            <div style={{ padding: '10px 0', maxHeight: 320, overflowY: 'auto' }}>
              {diffLines.map((line, i) => (
                <div key={i} className={line.type === 'add' ? 'diff-add' : line.type === 'remove' ? 'diff-remove' : ''}
                  style={{ padding: '1px 14px', fontFamily: 'var(--font-mono)', fontSize: 11.5, lineHeight: 1.6,
                    color: line.type === 'ctx' ? 'var(--text-dim)' : undefined,
                    background: line.type === 'ctx' ? undefined : undefined,
                  }}>
                  {line.text || '\u00a0'}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Feedback Dialog ─────────────────────────────────────────────────────────
function FeedbackDialog({ reportId, onClose, addToast }) {
  const [comment, setComment] = useStateR('');
  const [accepted, setAccepted] = useStateR(null);
  const [submitting, setSubmitting] = useStateR(false);

  const submit = () => {
    if (accepted === null) return;
    setSubmitting(true);
    setTimeout(() => {
      addToast('Feedback submitted — thank you!', 'success');
      onClose();
    }, 700);
  };

  return (
    <Dialog title="Submit Feedback" onClose={onClose}
      footer={
        <>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" onClick={submit} disabled={accepted === null || submitting}
            data-testid="send-feedback"
            icon={submitting ? <Spinner size={13} color="#fff" /> : null}>
            {submitting ? 'Submitting…' : 'Submit'}
          </Btn>
        </>
      }>
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 10 }}>Did this report meet your needs?</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {[{ val: true, label: '👍  Accept', color: 'var(--verified)', bg: 'var(--verified-bg)' }, { val: false, label: '👎  Reject', color: 'var(--blocked)', bg: 'var(--blocked-bg)' }].map(opt => (
            <button key={String(opt.val)} onClick={() => setAccepted(opt.val)}
              style={{
                flex: 1, padding: '9px 0', border: `1px solid ${accepted === opt.val ? opt.color : 'var(--border-subtle)'}`,
                borderRadius: 'var(--r)', background: accepted === opt.val ? opt.bg : 'var(--surface-raised)',
                color: accepted === opt.val ? opt.color : 'var(--text-muted)',
                fontSize: 13, fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
              }}>
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>Comments <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>(optional)</span></div>
        <textarea value={comment} onChange={e => setComment(e.target.value)}
          placeholder="What could be improved? Incorrect claims, missing sources, unclear sections…"
          style={{ width: '100%', minHeight: 90, padding: '10px 12px', fontSize: 13, resize: 'vertical', borderRadius: 'var(--r)', lineHeight: 1.5 }} />
      </div>
    </Dialog>
  );
}

Object.assign(window, { ReportContent, SourcesTab, GuardrailsTab, RubricTab, VersionsTab, FeedbackDialog });
