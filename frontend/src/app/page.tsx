import Link from "next/link";
import { BrandMark } from "./brand-mark";
import { ResearchPreview } from "./research-preview";
import "./landing.css";

const CAPABILITIES = [
  {
    title: "Search the full context",
    detail: "Semantic and keyword retrieval look for relevant passages, even when the question and source use different wording.",
    meta: "HYBRID SEARCH",
  },
  {
    title: "Follow the relationship",
    detail: "A knowledge graph connects entities across documents, with provenance back to the text that supports each link.",
    meta: "GRAPH RETRIEVAL",
  },
  {
    title: "Inspect what is supported",
    detail: "Citations and verification states distinguish grounded answers from incomplete evidence and abstentions.",
    meta: "EVIDENCE REVIEW",
  },
];

export default function ProductPage() {
  return (
    <main className="trace-site">
      <header className="trace-nav">
        <Link className="trace-brand" href="/" aria-label="TraceGraph home">
          <BrandMark />
          <span>TRACEGRAPH</span>
        </Link>
        <nav className="trace-nav-links" aria-label="Primary navigation">
          <a href="#example">Product preview</a>
          <a href="#method">How it works</a>
          <a href="https://github.com/Iam-Grim-Reaper/tracegraph-ai" target="_blank" rel="noopener noreferrer">
            Source code <span aria-hidden="true">↗</span>
          </a>
        </nav>
        <Link className="trace-nav-action" href="/app">
          Open workspace <span aria-hidden="true">↗</span>
        </Link>
      </header>

      <section className="trace-intro" aria-labelledby="trace-headline">
        <div className="trace-intro-main">
          <p className="trace-intro-eyebrow">TRACEGRAPH — DOCUMENT RESEARCH</p>
          <h1 id="trace-headline">
            The source is part
            <br />
            <span>of the answer.</span>
          </h1>
        </div>
        <div className="trace-intro-aside">
          <p>
            Search across documents and their relationships. See the passages
            supporting a response, not just the response itself.
          </p>
          <Link href="/app" className="trace-primary-link">
            Start researching <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </section>

      <ResearchPreview />

      <section className="trace-method" id="method" aria-labelledby="trace-method-title">
        <div className="trace-method-intro">
          <p className="trace-section-label">BUILT FOR REAL RESEARCH</p>
          <h2 id="trace-method-title">From a question to<br />something you can check.</h2>
          <p>TraceGraph brings document search, linked facts, and evidence inspection into one workspace.</p>
        </div>
        <div className="trace-method-list">
          {CAPABILITIES.map((capability) => (
            <article className="trace-method-item" key={capability.title}>
              <div className="trace-method-item-heading">
                <h3>{capability.title}</h3>
                <span aria-hidden="true">↗</span>
              </div>
              <p>{capability.detail}</p>
              <span className="trace-method-meta">{capability.meta}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="trace-bottom-cta" aria-label="Open TraceGraph">
        <div>
          <p className="trace-section-label">THE WORKSPACE</p>
          <h2>Your documents.<br />Your questions.</h2>
        </div>
        <Link href="/app">Open the research desk <span aria-hidden="true">↗</span></Link>
      </section>

      <footer className="trace-footer">
        <Link href="/" className="trace-footer-brand"><BrandMark /> TRACEGRAPH</Link>
        <p>Designed and engineered by Shriyans Denis.</p>
        <a href="https://github.com/Iam-Grim-Reaper/tracegraph-ai" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
      </footer>
    </main>
  );
}
