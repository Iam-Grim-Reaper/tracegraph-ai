"use client";

import { useState } from "react";

const PAPER_URL =
  "https://openaccess.thecvf.com/content_iccv_2017/html/Selvaraju_Grad-CAM_Visual_Explanations_ICCV_2017_paper.html";

const SOURCES = [
  {
    id: 1,
    name: "Paper authors",
    locator: "ICCV 2017 · Author list",
    heading: "Who introduced it",
    summary:
      "The 2017 publication credits Ramprasaath R. Selvaraju, Michael Cogswell, Abhishek Das, Ramakrishna Vedantam, Devi Parikh, and Dhruv Batra.",
    context: "The credited authors are directly associated with the Grad-CAM method in the original publication.",
  },
  {
    id: 2,
    name: "Method description",
    locator: "ICCV 2017 · Abstract",
    heading: "How it works",
    summary:
      "Grad-CAM uses gradients flowing into a convolutional network's final convolutional layer to produce a coarse map of the image regions important to a target prediction.",
    context: "The method is described as applicable across multiple CNN-based model families without requiring retraining.",
  },
] as const;

type SourceIndex = 0 | 1;

export function ResearchPreview() {
  const [selected, setSelected] = useState<SourceIndex>(0);
  const source = SOURCES[selected];

  return (
    <section className="trace-preview-section" id="example" aria-labelledby="trace-preview-heading">
      <div className="trace-preview-intro">
        <div>
          <p className="trace-section-label">INSIDE THE WORKSPACE</p>
          <h2 id="trace-preview-heading">The answer, with its evidence.</h2>
        </div>
        <span className="trace-preview-disclaimer">
          INTERACTIVE EXAMPLE · NOT A LIVE QUERY
        </span>
      </div>

      <div className="trace-preview">
        <div className="trace-preview-toolbar">
          <div className="trace-preview-title">
            <span className="trace-preview-symbol" aria-hidden="true">≡</span>
            <span>Research session</span>
          </div>
          <span className="trace-preview-mode">SAMPLE DOCUMENT / ICCV 2017</span>
        </div>

        <div className="trace-preview-question">
          <div className="trace-preview-field-label">QUESTION</div>
          <p>Who developed Grad-CAM, and what does it explain?</p>
        </div>

        <div className="trace-preview-content">
          <div className="trace-preview-research">
            <div className="trace-preview-answer-head">
              <span>ANSWER</span>
              <span className="trace-sample-marker">ILLUSTRATIVE RESULT</span>
            </div>

            <div className="trace-preview-answer">
              <p>
                Grad-CAM was introduced by <strong>Ramprasaath R. Selvaraju and
                collaborators</strong> in a paper published at ICCV 2017{" "}
                <button
                  className={selected === 0 ? "trace-citation is-active" : "trace-citation"}
                  type="button"
                  onClick={() => setSelected(0)}
                  aria-pressed={selected === 0}
                  aria-label="Inspect source 1, authorship"
                >
                  [1]
                </button>.
              </p>
              <p>
                It produces a visual map of the image regions influencing a
                convolutional neural network&apos;s prediction, using gradients
                from the final convolutional layer{" "}
                <button
                  className={selected === 1 ? "trace-citation is-active" : "trace-citation"}
                  type="button"
                  onClick={() => setSelected(1)}
                  aria-pressed={selected === 1}
                  aria-label="Inspect source 2, method"
                >
                  [2]
                </button>.
              </p>
            </div>

            <div className="trace-relationship">
              <div className="trace-relationship-head">
                <span>CONNECTED FACT</span>
                <span>DOCUMENT → ENTITY GRAPH</span>
              </div>
              <div className="trace-relationship-line" aria-label="Illustrative graph relationship: Selvaraju and collaborators introduced Grad-CAM">
                <span className="trace-relationship-entity">Selvaraju et al.</span>
                <span className="trace-relationship-edge"><small>INTRODUCED</small><span aria-hidden="true">→</span></span>
                <span className="trace-relationship-entity is-end">Grad-CAM</span>
              </div>
              <p>Evidence-linked relationships supplement document search.</p>
            </div>
          </div>

          <aside className="trace-source-panel" aria-label="Example source inspection">
            <div className="trace-source-topline">
              <span>SOURCE INSPECTOR</span>
              <span>02 REFERENCES</span>
            </div>
            <div className="trace-source-tabs" role="group" aria-label="Choose evidence to inspect">
              {SOURCES.map((item, index) => (
                <button
                  type="button"
                  key={item.id}
                  className={selected === index ? "trace-source-tab is-selected" : "trace-source-tab"}
                  onClick={() => setSelected(index as SourceIndex)}
                  aria-pressed={selected === index}
                >
                  <span className="trace-source-index">0{item.id}</span>
                  <span className="trace-source-name">{item.name}</span>
                  <span className="trace-source-tab-arrow" aria-hidden="true">↗</span>
                </button>
              ))}
            </div>
            <div className="trace-source-detail" aria-live="polite" aria-atomic="true">
              <span className="trace-source-locator">{source.locator}</span>
              <h3>{source.heading}</h3>
              <p>{source.summary}</p>
              <div className="trace-source-context">{source.context}</div>
              <a href={PAPER_URL} target="_blank" rel="noopener noreferrer">
                Open original publication <span aria-hidden="true">↗</span>
              </a>
            </div>
          </aside>
        </div>
      </div>
      <p className="trace-preview-footnote">
        This example is assembled from a published paper to demonstrate the
        interface. It is not generated by a live TraceGraph session.
        Select a citation or source to inspect its context.
      </p>
    </section>
  );
}
