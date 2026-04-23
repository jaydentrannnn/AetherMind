// Agent Trace panel — simulated SSE streaming
const { useState: useStateT, useEffect: useEffectT, useRef: useRefT } = React;

function AgentTrace({ running, onComplete }) {
  const [events, setEvents] = useStateT([]);
  const [expanded, setExpanded] = useStateT({});
  const [done, setDone] = useStateT(false);
  const scrollRef = useRefT(null);
  const timerRef = useRefT(null);
  const [copied, setCopied] = useStateT(false);

  useEffectT(() => {
    if (!running) return;
    setEvents([]); setDone(false);
    let i = 0;
    const schedule = () => {
      if (i >= MOCK_TRACE_EVENTS.length) { setDone(true); onComplete && onComplete(); return; }
      const ev = MOCK_TRACE_EVENTS[i];
      const delay = i === 0 ? 300 : ev.ts - MOCK_TRACE_EVENTS[i - 1].ts;
      timerRef.current = setTimeout(() => {
        setEvents(prev => [...prev, ev]);
        i++;
        schedule();
      }, Math.max(delay * 0.55, 80));
    };
    schedule();
    return () => clearTimeout(timerRef.current);
  }, [running]);

  useEffectT(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const copyDebug = () => {
    const bundle = JSON.stringify({ trace_id: MOCK_REPORT.trace_id, request_id: MOCK_REPORT.request_id, events }, null, 2);
    navigator.clipboard?.writeText(bundle).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lastType = events[events.length - 1]?.type;
  const isStreaming = running && !done;

  return (
    <div className="trace-panel">
      <div className="trace-header">
        <span className="trace-title">Agent Trace</span>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {isStreaming && (
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--progress)', fontFamily: 'var(--font-mono)' }}>
              <Spinner size={10} color="var(--progress)" /> streaming
            </span>
          )}
          {done && (
            <span style={{ fontSize: 11, color: 'var(--verified)', fontFamily: 'var(--font-mono)' }}>✓ done</span>
          )}
          <Btn variant="ghost" size="sm" onClick={copyDebug}
            title="Copy debug bundle" aria-label="Copy debug bundle"
            style={{ fontSize: 11, color: copied ? 'var(--verified)' : undefined }}>
            {copied ? <Icons.Check /> : <Icons.Copy />}
          </Btn>
        </div>
      </div>

      <div className="trace-scroll" ref={scrollRef}>
        {events.length === 0 && isStreaming && (
          <div style={{ padding: '16px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              <Spinner size={11} color="var(--text-dim)" />
              Initializing…
            </div>
          </div>
        )}
        {events.map(ev => (
          <TraceEvent key={ev.id} ev={ev} expanded={!!expanded[ev.id]} onToggle={() => setExpanded(p => ({ ...p, [ev.id]: !p[ev.id] }))} />
        ))}
        {isStreaming && events.length > 0 && (
          <div style={{ padding: '4px 14px 8px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="trace-spinner" />
            <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              {lastType === 'synth' ? 'synthesizing…' : lastType === 'guardrails' ? 'verifying…' : lastType === 'critic' ? 'evaluating…' : 'processing…'}
            </span>
          </div>
        )}
      </div>

      {/* Stats bar */}
      {done && (
        <div style={{
          padding: '8px 14px', borderTop: '1px solid var(--border-subtle)',
          display: 'flex', gap: 12, flexShrink: 0,
          fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)',
        }}>
          <span>{events.length} events</span>
          <span>·</span>
          <span style={{ color: 'var(--verified)' }}>7/8 verified</span>
          <span>·</span>
          <span>~8s</span>
        </div>
      )}
    </div>
  );
}

function TraceEvent({ ev, expanded, onToggle }) {
  const hasDetail = !!ev.detail;
  return (
    <div className={`trace-event ${ev.type}`} onClick={hasDetail ? onToggle : undefined}
      style={{ cursor: hasDetail ? 'pointer' : 'default' }}>
      <div className="trace-event-header">
        <span className={`trace-tag ${ev.tag}`}>{ev.tag}</span>
        <span style={{ color: 'var(--text)', fontSize: 11.5, flex: 1, minWidth: 0 }}>{ev.msg}</span>
        {ev.latency && <span className="trace-latency">{ev.latency}</span>}
        {hasDetail && (
          <span style={{ fontSize: 10, color: 'var(--text-dim)', marginLeft: 4 }}>
            {expanded ? '▲' : '▼'}
          </span>
        )}
      </div>
      {expanded && ev.detail && (
        <pre style={{
          marginTop: 6, fontSize: 10.5, color: 'var(--text-muted)',
          background: 'var(--surface)', borderRadius: 3, padding: '6px 8px',
          whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.5,
          fontFamily: 'var(--font-mono)',
        }}>
          {ev.detail}
        </pre>
      )}
    </div>
  );
}

Object.assign(window, { AgentTrace });
