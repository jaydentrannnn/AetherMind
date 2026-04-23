// Mock data — derived from backend/app/schemas/models.py shapes
// Confirm all field names against OpenAPI when available

const MOCK_SOURCES = [
  { id: "s1", title: "Emergent Abilities of Large Language Models", url: "https://arxiv.org/abs/2206.07682", domain: "arxiv.org", snippet: "We define emergent abilities as those that are not present in smaller models but emerge in larger models, often sharply and unpredictably.", verified: true, type: "arxiv" },
  { id: "s2", title: "In-context Learning and Induction Heads", url: "https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html", domain: "transformer-circuits.pub", snippet: "Induction heads are a circuit that appears to implement a simple form of in-context learning, completing patterns across multiple tokens.", verified: true, type: "web" },
  { id: "s3", title: "Scaling Laws for Neural Language Models", url: "https://arxiv.org/abs/2001.08361", domain: "arxiv.org", snippet: "Language model performance depends on scale: model parameters, dataset size, and compute budget according to power-law relationships.", verified: true, type: "arxiv" },
  { id: "s4", title: "A Mathematical Framework for Transformer Circuits", url: "https://transformer-circuits.pub/2021/framework/index.html", domain: "transformer-circuits.pub", snippet: "We introduce a mathematical framework for studying transformer circuits, enabling analysis of how attention heads compose to compute.", verified: true, type: "web" },
  { id: "s5", title: "Are Emergent Abilities of LLMs a Mirage?", url: "https://arxiv.org/abs/2304.15004", domain: "arxiv.org", snippet: "We suggest that emergent abilities may be partially an artifact of the metrics used for evaluation rather than a fundamental property.", verified: false, type: "arxiv" },
  { id: "s6", title: "Attention Is All You Need", url: "https://arxiv.org/abs/1706.03762", domain: "arxiv.org", snippet: "The dominant sequence transduction models are based on recurrent or convolutional neural networks. We propose the Transformer, a model architecture based solely on attention mechanisms.", verified: true, type: "arxiv" },
  { id: "s7", title: "Grokking: Generalization Beyond Overfitting", url: "https://arxiv.org/abs/2201.02177", domain: "arxiv.org", snippet: "We report that neural networks trained on small algorithmic datasets begin by memorizing before transitioning to generalization, sometimes well after apparent convergence.", verified: true, type: "arxiv" },
  { id: "s8", title: "Interpretability in the Wild: GPT-2 Small", url: "https://arxiv.org/abs/2209.11895", domain: "arxiv.org", snippet: "We identify circuits in GPT-2 small responsible for indirect object identification, providing mechanistic evidence for structured feature reuse.", verified: true, type: "arxiv" },
];

const MOCK_REPORT = {
  id: "rpt-ae7f21b",
  job_id: "job-ae7f21b",
  title: "Transformer Attention Mechanisms and Emergent Capabilities in Large Language Models",
  summary: "This report synthesizes current understanding of how transformer attention mechanisms give rise to emergent capabilities in large language models, examining evidence from scaling laws, mechanistic interpretability, and theoretical frameworks. The evidence suggests emergence is real but its causes remain contested.",
  created_at: "2026-04-21T14:32:11Z",
  depth: "deep",
  sections: [
    {
      id: "sec-1",
      title: "Background: Transformer Attention",
      content: [
        { type: "p", text: "The transformer architecture, introduced by Vaswani et al. (2017), replaces recurrent computation with self-attention: each token attends to all others via learned query-key-value projections.", citations: ["s6"] },
        { type: "p", text: "Multi-head attention allows the model to jointly attend to information from different representation subspaces. Each attention head independently computes attention weights, and outputs are concatenated and projected.", citations: ["s6"] },
        { type: "p", text: "The mathematical framework of Elhage et al. (2021) shows that attention heads can be understood as moving information between token positions via low-rank bilinear operations on the residual stream.", citations: ["s4"] },
      ]
    },
    {
      id: "sec-2",
      title: "Defining Emergent Capabilities",
      content: [
        { type: "p", text: "Wei et al. (2022) define emergent abilities as capabilities absent in smaller models that appear in larger ones — often sharply and unpredictably, not as a gradual continuation of smaller-scale trends.", citations: ["s1"] },
        { type: "p", text: "Examples include multi-step arithmetic, chain-of-thought reasoning, and novel analogical reasoning tasks. These tasks typically require composing multiple sub-skills that each individually scale smoothly.", citations: ["s1", "s3"] },
        {
          type: "table",
          headers: ["Capability", "Approximate Threshold", "Evidence Type"],
          rows: [
            ["Chain-of-Thought", "~100B params", "Empirical"],
            ["Arithmetic (multi-digit)", "~50B params", "Empirical"],
            ["Analogical reasoning", "~70B params", "Empirical"],
            ["In-context few-shot", "~10B params", "Empirical"],
          ]
        },
        { type: "p", text: "However, Schaeffer et al. (2023) argue that emergence may be an artifact of non-linear or discontinuous evaluation metrics — a smooth underlying capability can appear emergent if measured with a threshold metric.", citations: ["s5"] },
      ]
    },
    {
      id: "sec-3",
      title: "Mechanistic Interpretability: Induction Heads",
      content: [
        { type: "p", text: "Olsson et al. (2022) identify induction heads as a two-head circuit that enables in-context learning. One head copies previous token context; the other attends to positions following that context, enabling pattern completion across the sequence.", citations: ["s2"] },
        { type: "p", text: "This circuit forms a phase transition during training: models without induction heads show in-context learning loss curves that do not improve; models with them improve substantially. This constitutes a mechanistic account of one form of emergence.", citations: ["s2", "s4"] },
        { type: "p", text: "Wang et al. (2022) identify circuits responsible for indirect object identification in GPT-2 small, demonstrating that multi-head attention composes across layers to perform structured named-entity resolution.", citations: ["s8"] },
      ]
    },
    {
      id: "sec-4",
      title: "Scaling Laws and Phase Transitions",
      content: [
        { type: "p", text: "Kaplan et al. (2020) establish that language model cross-entropy loss follows power laws in model size N, data D, and compute C, with clear separation of regimes. Emergent tasks, however, may require combinations of capabilities that don't individually predict task-level phase transitions.", citations: ["s3"] },
        { type: "p", text: "Power et al. (2022) describe grokking — a phase transition from memorization to generalization that occurs long after apparent training convergence. This provides evidence that capability acquisition can be discontinuous in training even on small algorithmic tasks.", citations: ["s7"] },
      ]
    },
    {
      id: "sec-5",
      title: "Synthesis and Implications",
      content: [
        { type: "p", text: "The evidence is consistent with a picture where attention mechanisms enable compositional computation through circuit formation. Emergence at the task level can arise from threshold effects on composed capabilities, or from changes in measurement, or both.", citations: ["s1", "s2", "s4"] },
        { type: "p", text: "From a safety perspective, emergent capabilities imply that scale-based risk assessments may be unreliable if capabilities appear discontinuously. Mechanistic interpretability research on attention circuits provides the most tractable path toward predicting emergent capabilities before they appear.", citations: ["s1", "s5"] },
      ]
    }
  ],
  sources: MOCK_SOURCES,
  guardrails: {
    unverified_claims: [
      { claim: "Emergent abilities are absent at smaller scales", rationale: "Source s5 disputes this framing as metric-dependent", source_ids: ["s5"] },
    ],
    policy_violations: [],
    closure_violations: [
      { claim: "Chain-of-thought emerges at exactly 100B parameters", rationale: "Threshold is approximate and task-dependent; revised to 'approximately'", source_ids: ["s1"] },
    ]
  },
  rubric: {
    depth: { score: 4, max: 5, label: "Depth of Analysis" },
    citations: { score: 5, max: 5, label: "Citation Quality" },
    clarity: { score: 5, max: 5, label: "Clarity & Structure" },
    coverage: { score: 4, max: 5, label: "Topic Coverage" },
    accuracy: { score: 4, max: 5, label: "Factual Accuracy" },
  },
  versions: [
    { id: "v1", created_at: "2026-04-21T14:28:00Z", label: "Draft v1", summary_diff: "Initial synthesis; 5 sources, no revision." },
    { id: "v2", created_at: "2026-04-21T14:30:44Z", label: "Revised v2", summary_diff: "Guardrails revision: softened emergence threshold claim; added Schaeffer citation." },
    { id: "v3", created_at: "2026-04-21T14:32:11Z", label: "Final v3 (current)", summary_diff: "Critic pass: expanded Implications section; improved table formatting." },
  ],
  trace_id: "lf-trace-9b2ca4f1",
  request_id: "req-1714704731-ae7f",
};

const MOCK_TRACE_EVENTS = [
  { id: 1,  type: "planner",    tag: "planner",    msg: "Decomposing topic into sub-questions",         ts: 0 },
  { id: 2,  type: "planner",    tag: "planner",    msg: "Generated 6 sub-questions",                    ts: 600, detail: "1. What is transformer attention?\n2. How is emergence defined?\n3. What are induction heads?\n4. What do scaling laws predict?\n5. Is emergence an artifact?\n6. Implications for safety?" },
  { id: 3,  type: "researcher", tag: "researcher", msg: "Fan-out: launching 6 parallel queries",        ts: 900 },
  { id: 4,  type: "tool",       tag: "tool",       msg: "web_search: transformer attention mechanisms", ts: 1100, latency: "94ms" },
  { id: 5,  type: "tool",       tag: "tool",       msg: "arxiv: emergent abilities LLMs",               ts: 1150, latency: "312ms" },
  { id: 6,  type: "tool",       tag: "tool",       msg: "web_search: induction heads circuits",         ts: 1200, latency: "88ms" },
  { id: 7,  type: "tool",       tag: "tool",       msg: "arxiv: scaling laws neural language models",   ts: 1300, latency: "274ms" },
  { id: 8,  type: "tool",       tag: "tool",       msg: "pdf_fetch: Vaswani et al. 2017",               ts: 1400, latency: "521ms" },
  { id: 9,  type: "tool",       tag: "tool",       msg: "arxiv: grokking generalization phase",         ts: 1450, latency: "298ms" },
  { id: 10, type: "researcher", tag: "researcher", msg: "Collected 8 sources, 34 chunks indexed",       ts: 2400 },
  { id: 11, type: "synth",      tag: "synth",      msg: "Synthesizing: merging source clusters",        ts: 2600 },
  { id: 12, type: "synth",      tag: "synth",      msg: "Drafting section 1/5: Background",             ts: 3100 },
  { id: 13, type: "synth",      tag: "synth",      msg: "Drafting section 2/5: Emergence",              ts: 3500 },
  { id: 14, type: "synth",      tag: "synth",      msg: "Drafting section 3/5: Induction Heads",        ts: 3900 },
  { id: 15, type: "synth",      tag: "synth",      msg: "Drafting sections 4–5",                        ts: 4200 },
  { id: 16, type: "guardrails", tag: "guardrails", msg: "Citation verification: 7/8 verified",          ts: 4800, detail: "Unverified: s5 (disputed claim)" },
  { id: 17, type: "guardrails", tag: "guardrails", msg: "Policy check: PASS",                           ts: 5000 },
  { id: 18, type: "guardrails", tag: "guardrails", msg: "Closure check: 1 claim flagged for revision",  ts: 5200 },
  { id: 19, type: "critic",     tag: "critic",     msg: "Rubric evaluation running",                    ts: 5500 },
  { id: 20, type: "critic",     tag: "critic",     msg: "Scores: Depth 4 · Citations 5 · Clarity 5 · Coverage 4 · Accuracy 4", ts: 6000 },
  { id: 21, type: "revision",   tag: "revision",   msg: "Revision pass 1: softening emergence threshold claim", ts: 6300 },
  { id: 22, type: "revision",   tag: "revision",   msg: "Revision complete — diff applied",             ts: 7100 },
  { id: 23, type: "memory",     tag: "memory",     msg: "Writing report to SQLite",                     ts: 7400 },
  { id: 24, type: "memory",     tag: "memory",     msg: "Indexing 34 chunks into Chroma",               ts: 7600 },
  { id: 25, type: "done",       tag: "done",       msg: "Report finalized · job-ae7f21b",               ts: 8000 },
];

const MOCK_PREFERENCES = [
  { key: "response_language", value: "en", source: "user", updatedAt: "2026-04-18" },
  { key: "citation_style", value: "inline", source: "user", updatedAt: "2026-04-19" },
  { key: "default_depth", value: "standard", source: "inferred", updatedAt: "2026-04-20" },
  { key: "preferred_output_format", value: "structured_sections", source: "user", updatedAt: "2026-04-15" },
  { key: "summarize_sources", value: "true", source: "inferred", updatedAt: "2026-04-21" },
];

const MOCK_ALLOW_DOMAINS = ["arxiv.org", "nature.com", "science.org", "semanticscholar.org"];
const MOCK_DENY_DOMAINS  = ["reddit.com", "quora.com"];

const MOCK_SEMANTIC_RESULTS = [
  { id: "rpt-b3c12", title: "Mechanistic Interpretability in Sparse Autoencoders", score: 0.94, snippet: "Analysis of feature decomposition in transformer residual streams using sparse autoencoders, revealing polysemantic neurons.", date: "2026-04-10" },
  { id: "rpt-c8d34", title: "Chain-of-Thought Prompting and Reasoning Depth", score: 0.87, snippet: "Systematic evaluation of chain-of-thought performance across model scales and arithmetic task complexities.", date: "2026-03-28" },
  { id: "rpt-d2a91", title: "Phase Transitions in Neural Network Generalization", score: 0.82, snippet: "Survey of grokking-like transitions in deep networks, examining the relationship between regularization and delayed generalization.", date: "2026-03-14" },
];

Object.assign(window, {
  MOCK_SOURCES, MOCK_REPORT, MOCK_TRACE_EVENTS,
  MOCK_PREFERENCES, MOCK_ALLOW_DOMAINS, MOCK_DENY_DOMAINS, MOCK_SEMANTIC_RESULTS
});
