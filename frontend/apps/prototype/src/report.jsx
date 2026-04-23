// ReportPage — composes AgentTrace + ReportMain
const { useState: useStateRP, useEffect: useEffectRP } = React;

function ReportPage({ jobId, navigate }) {
  const report = MOCK_REPORT; // In production: useSWR(`/reports/${jobId}`)
  const [running, setRunning] = useStateRP(true);
  const [traceComplete, setTraceComplete] = useStateRP(false);
  const [activeTab, setActiveTab] = useStateRP('report');
  const [showFeedback, setShowFeedback] = useStateRP(false);
  const [selectedVersion, setSelectedVersion] = useStateRP('v3');
  const [toasts, addToast] = useToasts();
  const [rightTab, setRightTab] = useStateRP('sources');

  // Simulate loading from localStorage persistence
  useEffectRP(() => {
    const key = `aethermind-report-${jobId}`;
    const saved = localStorage.getItem(key);
    if (saved === 'done') { setRunning(false); setTraceComplete(true); }
    else {
      localStorage.setItem(key, 'running');
    }
  }, [jobId]);

  const onTraceComplete = () => {
    setTraceComplete(true);
    setRunning(false);
    localStorage.setItem(`aethermind-report-${jobId}`, 'done');
  };

  const copyId = (val) => {
    navigator.clipboard?.writeText(val).catch(() => {});
    addToast(`Copied: ${val}`, 'success');
  };

  const tabs = [
    { id: 'report',     label: 'Report' },
    { id: 'sources',    label: 'Sources',    count: report.sources.length },
    { id: 'guardrails', label: 'Guardrails', count: report.guardrails.unverified_claims.length + report.guardrails.closure_violations.length },
    { id: 'rubric',     label: 'Rubric' },
    { id: 'versions',   label: 'Versions',   count: report.versions.length },
  ];

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden', height: '100%' }}>

      {/* Left: Agent Trace */}
      <AgentTrace running={running} onComplete={onTraceComplete} />

      {/* Right: Report content */}
      <div className="report-main">
        {/* Toolbar */}
        <div className="report-toolbar">
          <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
            {/* Version selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Version:</span>
              <select
                value={selectedVersion}
                onChange={e => setSelectedVersion(e.target.value)}
                style={{
                  background: 'var(--surface-raised)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r)',
                  padding: '4px 8px',
                  fontSize: 12, color: 'var(--text)', cursor: 'pointer',
                }}>
                {report.versions.map(v => (
                  <option key={v.id} value={v.id}>{v.label}</option>
                ))}
              </select>
            </div>
            <Btn variant="secondary" size="sm" onClick={() => setShowFeedback(true)}
              data-testid="open-feedback">
              Feedback
            </Btn>
          </div>
        </div>

        {/* Status banner while streaming */}
        {running && (
          <div style={{
            padding: '8px 20px',
            background: 'var(--progress-bg)',
            borderBottom: '1px solid var(--progress)',
            display: 'flex', alignItems: 'center', gap: 10,
            fontSize: 13, color: 'var(--progress)',
            fontFamily: 'var(--font-mono)', flexShrink: 0,
          }}>
            <Spinner size={12} color="var(--progress)" />
            Research in progress — report will update as sections are finalized
          </div>
        )}

        {/* Tab content */}
        <div className="report-body">
          {activeTab === 'report'     && <ReportContent report={report} loading={running && !traceComplete} />}
          {activeTab === 'sources'    && <SourcesTab sources={report.sources} />}
          {activeTab === 'guardrails' && <GuardrailsTab guardrails={report.guardrails} />}
          {activeTab === 'rubric'     && <RubricTab rubric={report.rubric} />}
          {activeTab === 'versions'   && <VersionsTab versions={report.versions} />}
        </div>

        {/* Diagnostics footer */}
        <div className="diagnostics-footer">
          <span>Diagnostics</span>
          <span style={{ color: 'var(--border)' }}>·</span>
          <span>trace_id:</span>
          <span
            style={{ color: 'var(--accent)', cursor: 'pointer' }}
            onClick={() => copyId(report.trace_id)}
            title="Click to copy"
          >{report.trace_id}</span>
          <span style={{ color: 'var(--border)' }}>·</span>
          <span>req:</span>
          <span
            style={{ color: 'var(--accent)', cursor: 'pointer' }}
            onClick={() => copyId(report.request_id)}
            title="Click to copy"
          >{report.request_id}</span>
          <span style={{ marginLeft: 'auto', color: 'var(--text-dim)' }}>
            NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
          </span>
        </div>
      </div>

      {/* Feedback dialog */}
      {showFeedback && (
        <FeedbackDialog
          reportId={report.id}
          onClose={() => setShowFeedback(false)}
          addToast={addToast}
        />
      )}

      <Toast toasts={toasts} />
    </div>
  );
}

Object.assign(window, { ReportPage });
