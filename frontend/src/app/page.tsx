"use client";

import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import {
  askTraceGraph,
  TraceGraphResponse,
} from "../../lib/tracegraph";


type ApiStatus =
  | "checking"
  | "healthy"
  | "offline";


const EXAMPLE_QUESTIONS = [
  "Who developed Grad-CAM?",
  "What accuracy did the model achieve?",
  "Which models were evaluated on LC25000?",
  "What interpretability method does ConvNeXt-Small use and who developed it?",
];


export default function Home() {
  const [apiStatus, setApiStatus] =
    useState<ApiStatus>("checking");

  const [question, setQuestion] =
    useState("");

  const [result, setResult] =
    useState<TraceGraphResponse | null>(
      null,
    );

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);


  useEffect(() => {
    const checkApi = async () => {
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL;

      if (!apiUrl) {
        setApiStatus("offline");
        return;
      }

      try {
        const response = await fetch(
          `${apiUrl}/health`,
        );

        if (!response.ok) {
          throw new Error(
            "API health check failed",
          );
        }

        const data =
          (await response.json()) as {
            status: string;
          };

        setApiStatus(
          data.status === "healthy"
            ? "healthy"
            : "offline",
        );
      } catch {
        setApiStatus("offline");
      }
    };

    checkApi();
  }, []);


  const submitQuestion = async (
    value?: string,
  ) => {
    const finalQuestion =
      (value ?? question).trim();

    if (!finalQuestion || loading) {
      return;
    }

    setQuestion(finalQuestion);
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response =
        await askTraceGraph(
          finalQuestion,
        );

      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "TraceGraph could not process the request.",
      );
    } finally {
      setLoading(false);
    }
  };


  const handleSubmit = (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    void submitQuestion();
  };


  return (
    <main className="min-h-screen bg-[#050505] text-white">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-[-20rem] h-[38rem] w-[38rem] -translate-x-1/2 rounded-full bg-violet-600/10 blur-[140px]" />

        <div className="absolute bottom-[-20rem] right-[-10rem] h-[35rem] w-[35rem] rounded-full bg-blue-500/10 blur-[140px]" />
      </div>

      <div className="relative mx-auto min-h-screen max-w-7xl px-5 py-6 md:px-8">
        <Header
          apiStatus={apiStatus}
        />

        <section className="mx-auto mt-20 max-w-4xl text-center">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs text-zinc-400">
            <span className="h-1.5 w-1.5 rounded-full bg-violet-400" />

            Context-Aware Agentic GraphRAG
          </div>

          <h1 className="text-4xl font-semibold tracking-[-0.04em] sm:text-5xl md:text-6xl">
            Ask your knowledge.
            <span className="block bg-gradient-to-r from-violet-300 via-white to-blue-300 bg-clip-text text-transparent">
              Trace the evidence.
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-7 text-zinc-400 md:text-lg">
            Hybrid retrieval, knowledge
            graphs, multi-hop reasoning,
            and agentic verification in one
            explainable RAG system.
          </p>
        </section>

        <section className="mx-auto mt-12 max-w-4xl">
          <form
            onSubmit={handleSubmit}
            className="rounded-3xl border border-white/10 bg-white/[0.035] p-3 shadow-2xl shadow-black/40 backdrop-blur-xl"
          >
            <textarea
              value={question}
              onChange={(event) =>
                setQuestion(
                  event.target.value,
                )
              }
              placeholder="Ask TraceGraph a question..."
              rows={3}
              disabled={loading}
              className="min-h-28 w-full resize-none bg-transparent px-4 py-4 text-base text-white outline-none placeholder:text-zinc-600"
            />

            <div className="flex items-center justify-between border-t border-white/[0.07] px-2 pt-3">
              <div className="hidden items-center gap-2 text-xs text-zinc-600 sm:flex">
                <span>
                  GraphRAG
                </span>

                <span>•</span>

                <span>
                  Hybrid Search
                </span>

                <span>•</span>

                <span>
                  Verified
                </span>
              </div>

              <button
                type="submit"
                disabled={
                  loading ||
                  !question.trim()
                }
                className="ml-auto rounded-xl bg-white px-5 py-2.5 text-sm font-medium text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {loading
                  ? "Reasoning..."
                  : "Ask TraceGraph"}
              </button>
            </div>
          </form>

          {!result &&
            !loading &&
            !error && (
              <ExampleQuestions
                onQuestion={
                  submitQuestion
                }
              />
            )}

          {loading && (
            <LoadingState />
          )}

          {error && (
            <ErrorState
              message={error}
            />
          )}

          {result && (
            <TraceGraphResult
              result={result}
            />
          )}
        </section>

        <footer className="mt-24 border-t border-white/[0.06] py-8 text-center text-xs text-zinc-700">
          TraceGraph AI ·
          Context-Aware Agentic
          GraphRAG Platform
        </footer>
      </div>
    </main>
  );
}


function Header({
  apiStatus,
}: {
  apiStatus: ApiStatus;
}) {
  const statusText = {
    checking: "Connecting",
    healthy: "System online",
    offline: "API offline",
  }[apiStatus];

  return (
    <header className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-violet-400/20 bg-violet-500/10 text-sm font-semibold text-violet-300">
          TG
        </div>

        <div>
          <div className="text-sm font-semibold tracking-tight">
            TraceGraph AI
          </div>

          <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-600">
            Agentic GraphRAG
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.03] px-3 py-2 text-xs text-zinc-500">
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            apiStatus === "healthy"
              ? "bg-emerald-400"
              : apiStatus ===
                  "checking"
                ? "bg-amber-400"
                : "bg-red-400"
          }`}
        />

        {statusText}
      </div>
    </header>
  );
}


function ExampleQuestions({
  onQuestion,
}: {
  onQuestion: (
    question: string,
  ) => Promise<void>;
}) {
  return (
    <div className="mt-7">
      <p className="mb-3 text-xs uppercase tracking-[0.16em] text-zinc-700">
        Try an example
      </p>

      <div className="grid gap-2 sm:grid-cols-2">
        {EXAMPLE_QUESTIONS.map(
          (item) => (
            <button
              key={item}
              onClick={() =>
                void onQuestion(item)
              }
              className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-4 py-3 text-left text-sm text-zinc-500 transition hover:border-white/15 hover:bg-white/[0.05] hover:text-zinc-300"
            >
              {item}
            </button>
          ),
        )}
      </div>
    </div>
  );
}


function LoadingState() {
  return (
    <section className="mt-8 rounded-3xl border border-white/[0.08] bg-white/[0.025] p-6">
      <div className="flex items-center gap-3">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-violet-400" />

        <span className="text-sm text-zinc-400">
          TraceGraph is retrieving
          and verifying evidence...
        </span>
      </div>

      <div className="mt-6 grid grid-cols-4 gap-2">
        {[
          "Route",
          "Retrieve",
          "Research",
          "Verify",
        ].map(
          (step, index) => (
            <div
              key={step}
              className="rounded-xl border border-white/[0.06] bg-black/20 p-3"
            >
              <div className="text-[10px] text-zinc-700">
                0{index + 1}
              </div>

              <div className="mt-1 text-xs text-zinc-500">
                {step}
              </div>
            </div>
          ),
        )}
      </div>
    </section>
  );
}


function ErrorState({
  message,
}: {
  message: string;
}) {
  return (
    <section className="mt-8 rounded-2xl border border-red-500/20 bg-red-500/[0.05] p-5">
      <p className="text-sm font-medium text-red-300">
        TraceGraph request failed
      </p>

      <p className="mt-2 text-sm text-red-300/60">
        {message}
      </p>
    </section>
  );
}


function TraceGraphResult({
  result,
}: {
  result: TraceGraphResponse;
}) {
  return (
    <section className="mt-8 overflow-hidden rounded-3xl border border-white/[0.09] bg-[#0a0a0a] shadow-2xl shadow-black/40">
      <div className="border-b border-white/[0.07] p-6 md:p-7">
        <div className="flex flex-wrap items-center gap-2">
          <RouteBadge
            route={result.route}
          />

          <span
            className={`rounded-full border px-3 py-1 text-[11px] font-medium ${
              result.verified
                ? "border-emerald-500/20 bg-emerald-500/[0.07] text-emerald-300"
                : "border-amber-500/20 bg-amber-500/[0.07] text-amber-300"
            }`}
          >
            {result.verified
              ? "✓ Verified"
              : "Verification incomplete"}
          </span>
        </div>

        <p className="mt-6 whitespace-pre-wrap text-[15px] leading-7 text-zinc-200 md:text-base">
          {result.answer}
        </p>

        {result.used_evidence_labels
          .length > 0 && (
          <div className="mt-6 flex flex-wrap gap-2">
            {result.used_evidence_labels.map(
              (label) => (
                <span
                  key={label}
                  className="rounded-lg border border-white/[0.08] bg-white/[0.035] px-2.5 py-1.5 font-mono text-[10px] text-zinc-500"
                >
                  {label}
                </span>
              ),
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 border-b border-white/[0.07] md:grid-cols-4">
        <Metric
          label="Retrieval"
          value={
            result.route.toUpperCase()
          }
        />

        <Metric
          label="Graph facts"
          value={String(
            result.graph_fact_count,
          )}
        />

        <Metric
          label="Evidence"
          value={String(
            result
              .used_evidence_labels
              .length,
          )}
        />

        <Metric
          label="Retries"
          value={String(
            result.retry_count,
          )}
        />
      </div>

      <div className="p-6 md:p-7">
        <p className="text-xs font-medium uppercase tracking-[0.15em] text-zinc-600">
          Agent execution path
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          <PipelineNode>
            Router
          </PipelineNode>

          <Arrow />

          <PipelineNode active>
            {result.route.toUpperCase()}
          </PipelineNode>

          <Arrow />

          <PipelineNode>
            Research
          </PipelineNode>

          <Arrow />

          <PipelineNode
            verified={
              result.verified
            }
          >
            Verification
          </PipelineNode>
        </div>

        {result.verification_reason && (
          <div className="mt-6 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
            <p className="text-[10px] uppercase tracking-[0.15em] text-zinc-700">
              Verification report
            </p>

            <p className="mt-2 text-xs leading-5 text-zinc-500">
              {
                result.verification_reason
              }
            </p>
          </div>
        )}

        {result.rewritten_question && (
          <div className="mt-4 rounded-xl border border-amber-500/10 bg-amber-500/[0.03] p-4">
            <p className="text-[10px] uppercase tracking-[0.15em] text-amber-500/60">
              Retry query
            </p>

            <p className="mt-2 text-xs text-zinc-500">
              {
                result.rewritten_question
              }
            </p>
          </div>
        )}
      </div>
    </section>
  );
}


function RouteBadge({
  route,
}: {
  route: string;
}) {
  return (
    <span className="rounded-full border border-violet-400/20 bg-violet-400/[0.07] px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-violet-300">
      {route} retrieval
    </span>
  );
}


function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="border-r border-t border-white/[0.07] p-5 first:border-l-0 md:border-t-0">
      <p className="text-[10px] uppercase tracking-[0.14em] text-zinc-700">
        {label}
      </p>

      <p className="mt-2 text-lg font-medium text-zinc-300">
        {value}
      </p>
    </div>
  );
}


function PipelineNode({
  children,
  active = false,
  verified = false,
}: {
  children: React.ReactNode;
  active?: boolean;
  verified?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border px-3 py-2 ${
        verified
          ? "border-emerald-500/20 bg-emerald-500/[0.05] text-emerald-300"
          : active
            ? "border-violet-500/20 bg-violet-500/[0.06] text-violet-300"
            : "border-white/[0.07] bg-white/[0.02] text-zinc-500"
      }`}
    >
      {children}
    </div>
  );
}


function Arrow() {
  return (
    <span className="text-zinc-700">
      →
    </span>
  );
}