import Link from "next/link";

import { HeroKnowledgeNetwork } from "./hero-knowledge-network";

export default function ProductPage() {
  return (
    <main className="product-site">
      <header className="site-nav">
        <Link className="wordmark" href="/" aria-label="TraceGraph home">
          TRACEGRAPH
        </Link>
        <nav className="site-nav-links" aria-label="Primary">
          <a className="nav-method" href="#method">The method</a>
          <Link className="nav-cta" href="/app">
            Open workspace <span aria-hidden="true">↗</span>
          </Link>
        </nav>
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
          <p className="hero-meta">A RESEARCH INSTRUMENT · NO BLACK BOX</p>
          <h2>
            Follow the answer.
            <br />
            Back to its source.
          </h2>
          <p>Ask questions across indexed documents. See the passages, relationships, and verification behind the response.</p>
          <Link href="/app" className="button button-dark">
            Start researching <span aria-hidden="true">↗</span>
          </Link>
        </div>
        <p className="hero-watermark">Made by Shriyans Denis</p>
      </section>
      <section className="method-strip" id="method" aria-labelledby="method-title">
        <div className="method-strip-heading">
          <p className="eyebrow">THE METHOD / 001—003</p>
          <h2 id="method-title">A question is just the beginning.</h2>
        </div>
        <div className="method-strip-steps">
          <article><span>01 / FIND</span><h3>Retrieve what matters.</h3><p>Combine text search with connected facts across your document collection.</p></article>
          <article><span>02 / CONNECT</span><h3>Follow the relationships.</h3><p>Explore how entities and passages support the same question.</p></article>
          <article><span>03 / VERIFY</span><h3>Inspect the evidence.</h3><p>Read the original excerpts and understand when an answer is uncertain.</p></article>
        </div>
        <p className="method-credit">TRACEGRAPH — AN EVIDENCE-FIRST RESEARCH WORKSPACE <span>DESIGNED BY SHRIYANS DENIS</span></p>
      </section>
    </main>
  );
}
