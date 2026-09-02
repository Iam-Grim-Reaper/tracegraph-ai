import Link from "next/link";

import { HeroKnowledgeNetwork } from "./hero-knowledge-network";

export default function ProductPage() {
  return (
    <main className="product-site">
      <header className="site-nav">
        <Link className="wordmark" href="/" aria-label="TraceGraph home">
          TRACEGRAPH
        </Link>
        <Link className="nav-cta" href="/app">
          Open app <span aria-hidden="true">↗</span>
        </Link>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-network" aria-hidden="true">
          <HeroKnowledgeNetwork />
        </div>
        <h1 id="hero-title" aria-label="TraceGraph">
          <span>TRACE</span>
          <span>GRAPH</span>
        </h1>
        <div className="hero-copy">
          <h2>
            Answers aren&apos;t enough.
            <br />
            Trace the evidence.
          </h2>
          <p>Evidence-first document intelligence using text and graph retrieval.</p>
          <Link href="/app" className="button button-dark">
            Open TraceGraph <span aria-hidden="true">→</span>
          </Link>
        </div>
        <p className="hero-watermark">Made by Shriyans Denis</p>
      </section>
    </main>
  );
}
