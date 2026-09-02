import {
  ChangeEvent,
  FormEvent,
  KeyboardEvent,
  ReactNode,
  useEffect,
  useRef,
  useState,
} from "react";
import Link from "next/link";

import {
  ChatStreamEvent,
  DocumentSummary,
  TraceGraphEvidence,
  TraceGraphResponse,
} from "../../../lib/tracegraph";

type ApiStatus = "checking" | "healthy" | "offline";

/* ---------------------------------------------------------------- */
/* App header                                                        */
/* ---------------------------------------------------------------- */

export function AppHeader({ apiStatus }: { apiStatus: ApiStatus }) {
  const statusText = { checking: "Connecting", healthy: "Online", offline: "Offline" }[apiStatus];
  return (
    <header className="app-header">
      <div className="app-header-brand">
        <Link className="wordmark" href="/" aria-label="TraceGraph home">TRACEGRAPH</Link>
      </div>
      <span className="app-header-status" aria-live="polite">
        <span className={`status-dot ${apiStatus}`} aria-hidden="true" />
        {statusText}
      </span>
    </header>
  );
}

/* ---------------------------------------------------------------- */
/* Document rail                                                     */
/* ---------------------------------------------------------------- */

export function DocumentRail({
  documents,
  loading,
  error,
  selectedDocumentIds,
  uploadLoading,
  uploadError,
  uploadMessage,
  uploadsEnabled,
  apiOnline,
  onToggleDocument,
  onClearScope,
  onRefresh,
  onUpload,
}: {
  documents: DocumentSummary[];
  loading: boolean;
  error: string | null;
  selectedDocumentIds: string[];
  uploadLoading: boolean;
  uploadError: string | null;
  uploadMessage: string | null;
  uploadsEnabled: boolean | null;
  apiOnline: boolean;
  onToggleDocument: (documentId: string) => void;
  onClearScope: () => void;
  onRefresh: () => void;
  onUpload: (file: File) => Promise<void>;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [filter, setFilter] = useState("");
  const filteredDocuments = documents.filter((document) =>
    document.filename.toLowerCase().includes(filter.trim().toLowerCase()),
  );

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      void onUpload(file);
    }
    event.target.value = "";
  };

  return (
    <aside className="doc-rail" aria-label="Documents">
      <div className="doc-rail-head">
        <div className="doc-rail-title">
          <h2>Documents</h2>
          <span>{documents.length}</span>
        </div>
        <button type="button" onClick={onRefresh} disabled={loading} className="doc-rail-refresh">
          Refresh
        </button>
      </div>

      <button
        type="button"
        onClick={onClearScope}
        aria-pressed={selectedDocumentIds.length === 0}
        className={selectedDocumentIds.length === 0 ? "doc-scope is-selected" : "doc-scope"}
      >
        <span>
          <span className="doc-scope-title">All documents</span>
          <span className="doc-scope-note">Default search scope</span>
        </span>
        <SelectionIndicator selected={selectedDocumentIds.length === 0} />
      </button>

      {documents.length > 0 && (
        <label className="doc-filter">
          <span className="sr-only">Filter documents</span>
          <input
            type="search"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Filter documents"
          />
        </label>
      )}

      <div className="doc-rail-list">
        {loading && <DocumentLoadingState />}
        {!loading && error && <InlineError title="Documents unavailable" message={error} />}
        {!loading && !error && documents.length === 0 && <DocumentEmptyState uploadsEnabled={uploadsEnabled} />}
        {!loading && !error && filteredDocuments.length === 0 && documents.length > 0 && (
          <p className="doc-rail-empty-filter">No documents match &ldquo;{filter}&rdquo;.</p>
        )}
        {!loading &&
          !error &&
          filteredDocuments.map((document) => {
            const selected = selectedDocumentIds.includes(document.document_id);
            return (
              <button
                key={document.document_id}
                type="button"
                aria-pressed={selected}
                onClick={() => onToggleDocument(document.document_id)}
                className={selected ? "doc-row is-selected" : "doc-row"}
              >
                <SelectionIndicator selected={selected} />
                <span className="doc-row-body">
                  <span className="doc-row-top">
                    <span className="doc-row-name">{document.filename}</span>
                    <span className="doc-row-type">{document.file_type}</span>
                  </span>
                  <span className="doc-row-meta">
                    Ready · {document.chunk_count} chunks
                  </span>
                </span>
              </button>
            );
          })}
      </div>

      <div className="doc-rail-upload">
        {uploadsEnabled === true ? (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md,.markdown,.docx,.pptx,.xlsx"
              className="sr-only"
              onChange={handleFileChange}
            />
            <button
              type="button"
              disabled={uploadLoading || !apiOnline}
              onClick={() => fileInputRef.current?.click()}
              className="doc-upload-button"
            >
              {uploadLoading ? "Indexing document…" : "+ Upload document"}
            </button>
            {uploadLoading && <p className="doc-upload-note">Indexing and preparing document evidence.</p>}
            {uploadMessage && <p className="doc-upload-note is-success">{uploadMessage}</p>}
            {uploadError && <p className="doc-upload-note is-error">Document indexing failed: {uploadError}</p>}
          </>
        ) : uploadsEnabled === false ? (
          <p className="doc-upload-note">Uploads are disabled in the public demo.</p>
        ) : null}
      </div>
    </aside>
  );
}

function SelectionIndicator({ selected }: { selected: boolean }) {
  return (
    <span className={selected ? "selection-indicator is-selected" : "selection-indicator"} aria-hidden="true">
      ✓
    </span>
  );
}

function DocumentLoadingState() {
  return (
    <div className="doc-rail-loading" aria-label="Loading documents">
      {[1, 2, 3, 4].map((item) => (
        <div key={item} className="doc-row-skeleton">
          <div className="skeleton-line skeleton-line-lg" />
          <div className="skeleton-line skeleton-line-sm" />
        </div>
      ))}
    </div>
  );
}

function DocumentEmptyState({ uploadsEnabled }: { uploadsEnabled: boolean | null }) {
  return (
    <div className="doc-rail-empty">
      <p>No documents yet</p>
      <p>{uploadsEnabled ? "Upload a PDF, TXT, Markdown, DOCX, PPTX, or XLSX file to begin." : "This public demo uses pre-indexed documents."}</p>
    </div>
  );
}

function InlineError({ title, message }: { title: string; message: string }) {
  return (
    <div className="inline-error">
      <p>{title}</p>
      <p>{message}</p>
    </div>
  );
}

/* ---------------------------------------------------------------- */
/* Research workspace: empty state, composer, suggestions            */
/* ---------------------------------------------------------------- */

export function WorkspaceIntro() {
  return (
    <div className="ask-intro">
      <h1>Ask anything<br />about your documents.</h1>
    </div>
  );
}

export function QuestionComposer({
  question,
  scopeLabel,
  loading,
  apiOffline,
  onChange,
  onSubmit,
}: {
  question: string;
  scopeLabel: string;
  loading: boolean;
  apiOffline: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <form onSubmit={onSubmit} className="composer">
      <label className="sr-only" htmlFor="tracegraph-question">Ask a question about your documents</label>
      <textarea
        id="tracegraph-question"
        value={question}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your documents…"
        rows={4}
        disabled={loading}
      />
      <div className="composer-bar">
        <span className="composer-scope" title={scopeLabel}>{scopeLabel.toUpperCase()}</span>
        <button type="submit" disabled={loading || !question.trim() || apiOffline}>
          {loading ? "Working…" : "Ask"} <span aria-hidden="true">↑</span>
        </button>
      </div>
    </form>
  );
}

export function ExampleQuestions({
  questions,
  onQuestion,
}: {
  questions: string[];
  onQuestion: (question: string) => Promise<void>;
}) {
  return (
    <section className="suggested" aria-label="Suggested questions">
      <p className="eyebrow">Suggested</p>
      <div className="suggested-list">
        {questions.map((item) => (
          <button key={item} type="button" onClick={() => void onQuestion(item)} className="suggested-row">
            {item}
          </button>
        ))}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- */
/* Streaming progress                                                 */
/* ---------------------------------------------------------------- */

export function LoadingState({
  scopeLabel,
  events,
  onStop,
}: {
  scopeLabel: string;
  events: ChatStreamEvent[];
  onStop: () => void;
}) {
  const visibleEvents = events.filter((event) => event.type !== "completed");

  return (
    <section className="stream-panel" aria-live="polite" aria-label="Live TraceGraph execution">
      <div className="stream-panel-head">
        <p className="eyebrow">Tracing evidence…</p>
        <button type="button" onClick={onStop} className="stream-stop">Stop</button>
      </div>
      <p className="stream-scope">Searching {scopeLabel}</p>
      <details className="stream-detail">
        <summary>View live execution</summary>
        <ol>
          {visibleEvents.map((event, index) => (
            <li key={`${event.type}-${event.id ?? index}-${event.status ?? ""}`}>
              <span>{progressTitle(event.type)}</span>
              {event.message && <span> — {event.message}</span>}
            </li>
          ))}
          {visibleEvents.length === 0 && <li>Waiting for execution events.</li>}
        </ol>
      </details>
    </section>
  );
}

/* ---------------------------------------------------------------- */
/* Errors                                                             */
/* ---------------------------------------------------------------- */

export function ErrorState({ message }: { message: string }) {
  return (
    <section className="error-panel" role="alert">
      <p className="eyebrow">Connection</p>
      <p className="error-panel-title">Unable to reach TraceGraph.</p>
      <p className="error-panel-message">{message}</p>
    </section>
  );
}

/* ---------------------------------------------------------------- */
/* Completed result                                                   */
/* ---------------------------------------------------------------- */

export function TraceGraphResult({
  result,
  documents,
  question,
  events,
}: {
  result: TraceGraphResponse;
  documents: DocumentSummary[];
  question: string;
  events: ChatStreamEvent[];
}) {
  const [selectedEvidence, setSelectedEvidence] = useState<TraceGraphEvidence | null>(null);
  const scopeNames =
    result.document_ids?.map((id) => documents.find((document) => document.document_id === id)?.filename ?? id) ?? [];
  const citedLabels = new Set(result.used_evidence_labels.map((label) => label.replace(/^\[|\]$/g, "")));
  const citedEvidence = result.evidence_items.filter((item) => citedLabels.has(item.label));
  const evidence = citedEvidence.length > 0 ? citedEvidence : result.evidence_items;
  const graphEvidence = evidence.filter((item) => item.kind === "graph" && item.graph_fact);

  return (
    <section className="result" aria-label="TraceGraph answer and evidence">
      <div className="result-block">
        <p className="eyebrow">Question</p>
        <p className="result-question">{question}</p>
      </div>

      <article className="result-block">
        <div className="result-answer-head">
          <p className="eyebrow">Answer</p>
          <VerificationStatus status={result.answer_status} verified={result.verified} />
        </div>
        <MarkdownAnswer value={result.answer} />
      </article>

      <section className="result-block" aria-labelledby="sources-heading">
        <div className="result-block-head">
          <h2 id="sources-heading">Sources</h2>
          <span>{String(evidence.length).padStart(2, "0")}</span>
        </div>
        {evidence.length > 0 ? (
          <div className="source-list">
            {evidence.map((item, index) => (
              <EvidenceRow key={`${item.label}-${index}`} evidence={item} index={index + 1} onOpen={() => setSelectedEvidence(item)} />
            ))}
          </div>
        ) : (
          <p className="result-empty-note">No source excerpts were returned for this response.</p>
        )}
      </section>

      {graphEvidence.length > 0 && (
        <details className="result-block result-collapsible">
          <summary>Graph evidence <span>({graphEvidence.length})</span></summary>
          <div className="graph-evidence-list">
            {graphEvidence.map((item) => (
              <GraphEvidenceRow key={item.label} evidence={item} onOpen={() => setSelectedEvidence(item)} />
            ))}
          </div>
        </details>
      )}

      <details className="result-block result-collapsible">
        <summary>How TraceGraph answered</summary>
        <AnswerMethod result={result} scopeNames={scopeNames} events={events} />
      </details>

      {selectedEvidence && <EvidenceDrawer evidence={selectedEvidence} onClose={() => setSelectedEvidence(null)} />}
    </section>
  );
}

function VerificationStatus({ status, verified }: { status: TraceGraphResponse["answer_status"]; verified: boolean }) {
  if (verified) {
    return <span className="verification-badge is-verified">✓ Verified</span>;
  }
  const label = {
    verified_answer: "Verified answer",
    verified_abstention: "Verified abstention",
    degraded_retrieval: "Limited evidence",
    partial_grounded_answer: "Partially grounded",
    grounded_abstention: "Grounded abstention",
  }[status];
  return <span className="verification-badge">{label}</span>;
}

function EvidenceRow({ evidence, index, onOpen }: { evidence: TraceGraphEvidence; index: number; onOpen: () => void }) {
  const sourceName = evidence.filename ?? "Indexed document";
  const locator = sourceLocator(evidence);
  return (
    <button type="button" onClick={onOpen} className="source-row">
      <span className="source-row-index">{String(index).padStart(2, "0")}</span>
      <span className="source-row-body">
        <span className="source-row-head">
          <span className="source-row-name">{sourceName}</span>
          <span className="source-row-locator">{locator}</span>
        </span>
        <span className="source-row-excerpt">&ldquo;{evidence.text || "Open source evidence"}&rdquo;</span>
      </span>
    </button>
  );
}

function GraphEvidenceRow({ evidence, onOpen }: { evidence: TraceGraphEvidence; onOpen: () => void }) {
  const fact = evidence.graph_fact!;
  return (
    <button type="button" onClick={onOpen} className="graph-evidence-row">
      <span className="graph-evidence-source">{fact.source}</span>
      <span className="graph-evidence-relationship">{fact.relationship}</span>
      <span className="graph-evidence-target">{fact.target}</span>
      <span className="graph-evidence-meta">{evidence.filename ?? "Indexed document"} · {sourceLocator(evidence)}</span>
    </button>
  );
}

function AnswerMethod({
  result,
  scopeNames,
  events,
}: {
  result: TraceGraphResponse;
  scopeNames: string[];
  events: ChatStreamEvent[];
}) {
  const route = titleCase(result.final_route ?? result.route);
  return (
    <div className="method">
      <div className="method-grid">
        <MethodItem label="Route" value={`${route} retrieval`} />
        <MethodItem label="Text evidence" value={`${result.hybrid_evidence_count} passages`} />
        <MethodItem label="Graph evidence" value={`${result.graph_evidence_count} facts`} />
        <MethodItem label="Verification" value={result.verified ? "Passed" : "Not confirmed"} />
      </div>
      {scopeNames.length > 0 && <MethodItem label="Scoped documents" value={scopeNames.join(", ")} />}
      {result.routing_reason && <MethodItem label="Routing decision" value={result.routing_reason} />}
      {result.decomposition_used && <Decomposition items={result.subquestions} />}
      {(result.degraded || result.decomposition_degraded) && (
        <p className="method-warning">Limited evidence: {result.degradation_reason ?? "The evidence set was incomplete."}</p>
      )}
      {result.verification_reason && <MethodItem label="Verification report" value={result.verification_reason} />}
      {events.length > 0 && (
        <div>
          <p className="method-label">Execution steps</p>
          <ol className="method-steps">
            {events.map((event, index) => (
              <li key={`${event.type}-${event.id ?? index}-${event.status ?? ""}`}>
                <span>{progressTitle(event.type)}</span>
                {event.message && <span> — {event.message}</span>}
              </li>
            ))}
          </ol>
        </div>
      )}
      <details className="method-technical">
        <summary>Technical metadata</summary>
        <p>
          Strategy: {result.strategy} · Initial route: {result.initial_route ?? "n/a"} · Retry count: {result.retry_count}
          <br />
          Top text relevance: {formatScore(result.hybrid_top_relevance)} · Top graph relevance: {formatScore(result.graph_top_relevance)}
          <br />
          Graph facts: {result.graph_fact_count} · Retrieved chunks: {result.retrieved_chunk_ids.length}
          {result.rewritten_question && <><br />Retry query: {result.rewritten_question}</>}
          {result.retrieved_chunk_ids.length > 0 && <><br />Chunk IDs: {result.retrieved_chunk_ids.join(", ")}</>}
        </p>
      </details>
    </div>
  );
}

function Decomposition({ items }: { items: TraceGraphResponse["subquestions"] }) {
  return (
    <div>
      <p className="method-label">Decomposition</p>
      <ol className="method-decomposition">
        {items.map((item, index) => (
          <li key={item.id}>
            <p>{index + 1}. {item.question}</p>
            <p>{item.evidence_count} evidence items · {item.route ?? "unresolved"} route</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

function MethodItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="method-item">
      <p className="method-label">{label}</p>
      <p className="method-value">{value}</p>
    </div>
  );
}

function EvidenceDrawer({ evidence, onClose }: { evidence: TraceGraphEvidence; onClose: () => void }) {
  useEffect(() => {
    const handler = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="evidence-drawer-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) {
          onClose();
        }
      }}
    >
      <aside role="dialog" aria-modal="true" aria-labelledby="evidence-title" className="evidence-drawer">
        <div className="evidence-drawer-head">
          <div>
            <p className="eyebrow">{evidence.kind === "graph" ? "Graph source" : "Source evidence"}</p>
            <h2 id="evidence-title">{evidence.filename ?? "Indexed document"}</h2>
          </div>
          <button type="button" onClick={onClose} autoFocus aria-label="Close evidence" className="evidence-drawer-close">
            Close
          </button>
        </div>
        <div className="evidence-drawer-meta">
          <span>{sourceLocator(evidence)}</span>
          <span>{titleCase(evidence.retrieval_route)} retrieval</span>
          {evidence.chunk_id && <span>Chunk {evidence.chunk_id}</span>}
        </div>
        {evidence.graph_fact && (
          <div className="evidence-drawer-fact">
            <p>{evidence.graph_fact.source}</p>
            <p>└─ {evidence.graph_fact.relationship} →</p>
            <p>{evidence.graph_fact.target}</p>
          </div>
        )}
        <div className="evidence-drawer-text">
          <p>{evidence.text || "No source excerpt was returned for this evidence item."}</p>
        </div>
        {evidence.subquestion && (
          <div className="evidence-drawer-subquestion">
            <p className="method-label">Used for</p>
            <p>{evidence.subquestion}</p>
          </div>
        )}
      </aside>
    </div>
  );
}

function MarkdownAnswer({ value }: { value: string }) {
  const nodes: ReactNode[] = [];
  const lines = value.replace(/<[^>]*>/g, "").split("\n");
  for (let index = 0; index < lines.length; ) {
    const line = lines[index].trim();
    if (!line) {
      index += 1;
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      nodes.push(
        <h3 key={index}>
          <InlineMarkdown value={heading[2]} />
        </h3>,
      );
      index += 1;
      continue;
    }
    const unordered = line.match(/^[-*]\s+(.+)$/);
    if (unordered) {
      const items: string[] = [];
      const start = index;
      while (index < lines.length) {
        const match = lines[index].trim().match(/^[-*]\s+(.+)$/);
        if (!match) {
          break;
        }
        items.push(match[1]);
        index += 1;
      }
      nodes.push(
        <ul key={start}>
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>
              <InlineMarkdown value={item} />
            </li>
          ))}
        </ul>,
      );
      continue;
    }
    const ordered = line.match(/^\d+[.)]\s+(.+)$/);
    if (ordered) {
      const items: string[] = [];
      const start = index;
      while (index < lines.length) {
        const match = lines[index].trim().match(/^\d+[.)]\s+(.+)$/);
        if (!match) {
          break;
        }
        items.push(match[1]);
        index += 1;
      }
      nodes.push(
        <ol key={start}>
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>
              <InlineMarkdown value={item} />
            </li>
          ))}
        </ol>,
      );
      continue;
    }
    nodes.push(
      <p key={index}>
        <InlineMarkdown value={line} />
      </p>,
    );
    index += 1;
  }
  return <div className="answer-body">{nodes}</div>;
}

function InlineMarkdown({ value }: { value: string }) {
  return (
    <>
      {value
        .split(/(`[^`]+`|\*\*[^*]+\*\*)/g)
        .filter(Boolean)
        .map((part, index) => {
          if (part.startsWith("`") && part.endsWith("`")) {
            return <code key={index}>{part.slice(1, -1)}</code>;
          }
          if (part.startsWith("**") && part.endsWith("**")) {
            return <strong key={index}>{part.slice(2, -2)}</strong>;
          }
          return <span key={index}>{part}</span>;
        })}
    </>
  );
}

function progressTitle(type: ChatStreamEvent["type"]): string {
  const titles: Record<ChatStreamEvent["type"], string> = {
    started: "Preparing request",
    routing: "Choosing retrieval route",
    retrieval: "Retrieving evidence",
    decomposition: "Breaking down the question",
    subquestion: "Researching subquestion",
    research: "Examining evidence",
    verification: "Verifying response",
    completed: "Response complete",
    error: "Execution issue",
  };
  return titles[type];
}

function sourceLocator(evidence: TraceGraphEvidence): string {
  if (evidence.source_locator?.label) {
    return evidence.source_locator.label;
  }
  if (evidence.page_number !== null) {
    return `Page ${evidence.page_number}`;
  }
  if (evidence.chunk_index !== null) {
    return `Section ${evidence.chunk_index + 1}`;
  }
  return evidence.kind === "graph" ? "Knowledge graph" : "Document excerpt";
}

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function formatScore(value: number | null): string {
  return value === null ? "Unavailable" : value.toFixed(3);
}
