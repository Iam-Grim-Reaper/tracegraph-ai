import Link from "next/link";
import { BrandMark } from "./brand-mark";

const STEPS = [
  {
    number: "01",
    name: "Retrieve",
    description: "Find relevant passages with semantic and keyword search. Keep the original document in view.",
    notation: "TEXT + VECTOR",
  },
  {
    number: "02",
    name: "Connect",
    description: "Follow people, concepts, and relationships through a document-linked knowledge graph.",
    notation: "ENTITY + CONTEXT",
  },
  {
    number: "03",
    name: "Verify",
    description: "Examine cited excerpts and surface uncertainty when the evidence doesn't support an answer.",
    notation: "CLAIM + SOURCE",
  },
];

export default function ProductPage() {
  return (
    <main className="product-site">
      <header className="site-nav">
        <Link className="wordmark" href="/" aria-label="TraceGraph home">
          <BrandMark />
          <span>TRACEGRAPH<span className="wordmark-suffix"> / AI</span></span>
        </Link>
        <div className="site-nav-links">
          <nav className="site-nav-menu" aria-label="Main navigation">
            <a className="nav-method" href="#approach">Method</a>
            <a className="nav-method" href="https://github.com/Iam-Grim-Reaper/tracegraph-ai" target="_blank" rel="noopener noreferrer">GitHub <span aria-hidden="true">↗</span></a>
          </nav>
          <Link className="nav-cta" href="/app">
            Launch workspace <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-intro">
          <p className="section-index"><span className="section-index-marker" /> DOCUMENT INTELLIGENCE / 001</p>
          <h1 id="hero-title">Answers,<br /><span>under scrutiny.</span></h1>
          <p className="hero-description">A serious research workspace for your documents. Find the connection, follow the evidence, and see where every answer comes from.</p>
          <div className="hero-actions">
            <Link className="button button-primary" href="/app">Enter workspace <span aria-hidden="true">↗</span></Link>
            <a className="button button-secondary" href="#approach">Explore the method <span aria-hidden="true">↓</span></a>
          </div>
          <div className="hero-fineprint">
            <span>HYBRID RETRIEVAL</span>
            <span aria-hidden="true" className="fineprint-separator" />
            <span>KNOWLEDGE GRAPHS</span>
            <span aria-hidden="true" className="fineprint-separator" />
            <span>SOURCE VERIFICATION</span>
          </div>
        </div>

        <div className="instrument" aria-label="Illustration of TraceGraph's evidence retrieval process">
          <div className="instrument-topline">
            <span>TRACE / PROTOCOL 001</span>
            <span className="instrument-caption">SCHEMATIC, NOT LIVE DATA</span>
          </div>
          <div className="instrument-viewport">
            <span className="instrument-coordinate">X: 01.08 / Y: 00.42</span>
            <div className="instrument-query">
              <span className="diagram-caption">INPUT / QUESTION</span>
              <strong>What connects these findings?</strong>
              <span className="diagram-square" aria-hidden="true">↗</span>
            </div>
            <div className="diagram-connector connector-one" aria-hidden="true"><span /></div>
            <div className="instrument-split">
              <div className="diagram-node">
                <span className="diagram-caption">PATH / 01</span>
                <strong>Document index</strong>
                <small>Semantic + lexical</small>
              </div>
              <div className="diagram-node">
                <span className="diagram-caption">PATH / 02</span>
                <strong>Knowledge graph</strong>
                <small>Entity relationships</small>
              </div>
            </div>
            <div className="diagram-connector connector-two" aria-hidden="true"><span /></div>
            <div className="instrument-output">
              <span className="diagram-caption">OUTPUT / EVIDENCE</span>
              <strong>Claims, connected to sources.</strong>
              <span className="instrument-check" aria-hidden="true">+</span>
            </div>
            <div className="instrument-bottom-axis" aria-hidden="true"><span>0</span><span>1</span><span>2</span><span>3</span><span>4</span><span>5</span></div>
          </div>
          <div className="instrument-footer">
            <span>FIG. 01 — RESEARCH FLOW</span>
            <span>TRACEABLE BY DESIGN</span>
          </div>
        </div>
      </section>

      <section className="approach" id="approach" aria-labelledby="approach-title">
        <div className="approach-intro">
          <p className="section-index">02 / THE METHOD</p>
          <h2 id="approach-title">A clearer path<br />from question to proof.</h2>
          <p>TraceGraph combines retrieval, relationships, and verification in one deliberate workflow.</p>
        </div>
        <div className="approach-steps">
          {STEPS.map((step) => (
            <article className="approach-step" key={step.number}>
              <div className="approach-step-top"><span>{step.number} / 03</span><span aria-hidden="true">↗</span></div>
              <h3>{step.name}</h3>
              <p>{step.description}</p>
              <span className="approach-step-notation">{step.notation}</span>
            </article>
          ))}
        </div>
      </section>

      <footer className="site-footer">
        <Link className="footer-brand" href="/"><BrandMark /> TRACEGRAPH</Link>
        <p>Evidence-first research, built with intention.</p>
        <span>DESIGNED & ENGINEERED BY SHRIYANS DENIS</span>
      </footer>
    </main>
  );
}
