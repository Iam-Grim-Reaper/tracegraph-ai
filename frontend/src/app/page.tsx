"use client";

import {
  ChangeEvent,
  FormEvent,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  API_URL,
  ChatStreamEvent,
  DocumentSummary,
  getDocuments,
  TraceGraphEvidence,
  TraceGraphResponse,
  streamTraceGraph,
  uploadDocument,
} from "../../lib/tracegraph";


type ApiStatus =
  | "checking"
  | "healthy"
  | "offline";


const DOMAIN_QUESTIONS: Record<
  string,
  string
> = {
  research:
    "Who developed Grad-CAM?",

  career:
    "Where did Alex Morgan work and what skills does Alex Morgan have?",

  policy:
    "What regulation governs the ACME Data Protection Policy?",

  contract:
    "What obligation does Northstar Analytics LLC have?",
};


const DEFAULT_QUESTIONS = [
  DOMAIN_QUESTIONS.research,
  DOMAIN_QUESTIONS.career,
  DOMAIN_QUESTIONS.policy,
  DOMAIN_QUESTIONS.contract,
];


export default function Home() {
  const [apiStatus, setApiStatus] =
    useState<ApiStatus>(
      "checking",
    );

  const [documents, setDocuments] =
    useState<DocumentSummary[]>(
      [],
    );

  const [
    documentsLoading,
    setDocumentsLoading,
  ] = useState(
    true,
  );

  const [
    documentsError,
    setDocumentsError,
  ] = useState<string | null>(
    null,
  );

  const [
    selectedDocumentIds,
    setSelectedDocumentIds,
  ] = useState<string[]>(
    [],
  );

  const [question, setQuestion] =
    useState("");

  const [result, setResult] =
    useState<TraceGraphResponse | null>(
      null,
    );

  const [loading, setLoading] =
    useState(
      false,
    );
  const [streamEvents, setStreamEvents] = useState<ChatStreamEvent[]>([]);
  const streamController = useRef<AbortController | null>(null);

  const [error, setError] =
    useState<string | null>(
      null,
    );

  const [
    uploadLoading,
    setUploadLoading,
  ] = useState(
    false,
  );

  const [
    uploadError,
    setUploadError,
  ] = useState<string | null>(
    null,
  );

  const [
    uploadMessage,
    setUploadMessage,
  ] = useState<string | null>(
    null,
  );


  const loadDocuments =
    useCallback(
      async () => {
        setDocumentsLoading(
          true,
        );

        setDocumentsError(
          null,
        );

        try {
          const response =
            await getDocuments();

          setDocuments(
            response.documents,
          );

          const validIds =
            new Set(
              response.documents.map(
                (document) =>
                  document.document_id,
              ),
            );

          setSelectedDocumentIds(
            (current) =>
              current.filter(
                (documentId) =>
                  validIds.has(
                    documentId,
                  ),
              ),
          );
        } catch (err) {
          setDocumentsError(
            err instanceof Error
              ? err.message
              : "Could not load documents.",
          );
        } finally {
          setDocumentsLoading(
            false,
          );
        }
      },
      [],
    );


  useEffect(() => {
    const initialize = async () => {
      try {
        const response =
          await fetch(
            `${API_URL}/health`,
          );

        if (!response.ok) {
          throw new Error(
            "API health check failed.",
          );
        }

        const data =
          (await response.json()) as {
            status: string;
          };

        setApiStatus(
          data.status ===
            "healthy"
            ? "healthy"
            : "offline",
        );
      } catch {
        setApiStatus(
          "offline",
        );
      }
    };

    void initialize();

    void loadDocuments();
  }, [
    loadDocuments,
  ]);

  useEffect(() => () => streamController.current?.abort(), []);


  const selectedDocuments =
    useMemo(
      () =>
        documents.filter(
          (document) =>
            selectedDocumentIds.includes(
              document.document_id,
            ),
        ),
      [
        documents,
        selectedDocumentIds,
      ],
    );


  const scopeLabel =
    useMemo(
      () => {
        if (
          selectedDocuments.length ===
          0
        ) {
          return documents.length ===
            1
            ? "All documents · 1 document"
            : `All documents · ${documents.length} documents`;
        }

        if (
          selectedDocuments.length ===
          1
        ) {
          return (
            selectedDocuments[0]
              .filename
          );
        }

        return `${selectedDocuments.length} documents selected`;
      },
      [
        documents.length,
        selectedDocuments,
      ],
    );


  const exampleQuestions =
    useMemo(
      () => {
        if (
          selectedDocuments.length ===
          0
        ) {
          return DEFAULT_QUESTIONS;
        }

        const profiles =
          new Set<string>();

        selectedDocuments.forEach(
          (document) => {
            document
              .ontology_profiles
              .forEach(
                (profile) => {
                  profiles.add(
                    profile,
                  );
                },
              );
          },
        );

        const questions =
          Array.from(
            profiles,
          )
            .map(
              (profile) =>
                DOMAIN_QUESTIONS[
                  profile
                ],
            )
            .filter(
              (
                item,
              ): item is string =>
                Boolean(item),
            );

        return questions.length >
          0
          ? questions.slice(
              0,
              4,
            )
          : DEFAULT_QUESTIONS;
      },
      [
        selectedDocuments,
      ],
    );


  const toggleDocument =
    (
      documentId: string,
    ) => {
      setSelectedDocumentIds(
        (current) => {
          if (
            current.includes(
              documentId,
            )
          ) {
            return current.filter(
              (id) =>
                id !==
                documentId,
            );
          }

          return [
            ...current,
            documentId,
          ];
        },
      );

      setResult(
        null,
      );

      setError(
        null,
      );
    };


  const clearDocumentScope =
    () => {
      setSelectedDocumentIds(
        [],
      );

      setResult(
        null,
      );

      setError(
        null,
      );
    };


  const submitQuestion =
    async (
      value?: string,
    ) => {
      const finalQuestion =
        (
          value ??
          question
        ).trim();

      if (
        !finalQuestion
      ) {
        return;
      }

      setQuestion(
        finalQuestion,
      );

      setLoading(
        true,
      );

      setError(
        null,
      );

      setResult(
        null,
      );
      setStreamEvents([]);
      streamController.current?.abort();
      const controller = new AbortController();
      streamController.current = controller;

      try {
        const response =
          await streamTraceGraph(
            finalQuestion,

            selectedDocumentIds
              .length > 0
              ? selectedDocumentIds
              : undefined,
            (event) => setStreamEvents((current) => [...current, event]),
            controller.signal,
          );

        setResult(
          response,
        );
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }
        setError(
          err instanceof Error
            ? err.message
            : "TraceGraph could not process the request.",
        );
      } finally {
        if (streamController.current === controller) {
          setLoading(false);
          streamController.current = null;
        }
      }
    };


  const handleSubmit =
    (
      event:
        FormEvent<HTMLFormElement>,
    ) => {
      event.preventDefault();

      void submitQuestion();
    };


  const handleUpload =
    async (
      file: File,
    ) => {
      if (
        uploadLoading
      ) {
        return;
      }

      setUploadLoading(
        true,
      );

      setUploadError(
        null,
      );

      setUploadMessage(
        null,
      );

      try {
        const uploaded =
          await uploadDocument(
            file,
          );

        await loadDocuments();

        setSelectedDocumentIds(
          [
            uploaded.document_id,
          ],
        );

        setUploadMessage(
          `${uploaded.filename} indexed as ${formatOntology(
            uploaded.ontology_profile,
          )}.`,
        );

        setResult(
          null,
        );
      } catch (err) {
        setUploadError(
          err instanceof Error
            ? err.message
            : "Document upload failed.",
        );
      } finally {
        setUploadLoading(
          false,
        );
      }
    };


  return (
    <main className="min-h-screen bg-[#050505] text-white">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-[-20rem] h-[38rem] w-[38rem] -translate-x-1/2 rounded-full bg-violet-600/10 blur-[140px]" />

        <div className="absolute bottom-[-20rem] right-[-10rem] h-[35rem] w-[35rem] rounded-full bg-blue-500/10 blur-[140px]" />
      </div>

      <div className="relative mx-auto min-h-screen max-w-7xl px-5 py-6 md:px-8">
        <Header
          apiStatus={
            apiStatus
          }
        />

        <section className="mx-auto mt-14 max-w-4xl text-center md:mt-16">
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
            Hybrid retrieval,
            knowledge graphs,
            multi-hop reasoning,
            ontology-aware indexing,
            and agentic verification
            in one explainable RAG
            system.
          </p>
        </section>

        <section className="mt-12 grid items-start gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
          <DocumentManager
            documents={
              documents
            }

            loading={
              documentsLoading
            }

            error={
              documentsError
            }

            selectedDocumentIds={
              selectedDocumentIds
            }

            uploadLoading={
              uploadLoading
            }

            uploadError={
              uploadError
            }

            uploadMessage={
              uploadMessage
            }

            apiOnline={
              apiStatus ===
              "healthy"
            }

            onToggleDocument={
              toggleDocument
            }

            onClearScope={
              clearDocumentScope
            }

            onRefresh={() =>
              void loadDocuments()
            }

            onUpload={
              handleUpload
            }
          />

          <div className="min-w-0">
            <ScopeBar
              selectedDocuments={
                selectedDocuments
              }

              documentCount={
                documents.length
              }

              scopeLabel={
                scopeLabel
              }
            />

            <form
              onSubmit={
                handleSubmit
              }

              className="mt-3 rounded-3xl border border-white/10 bg-white/[0.035] p-3 shadow-2xl shadow-black/40 backdrop-blur-xl"
            >
              <textarea
                value={
                  question
                }

                onChange={(
                  event,
                ) =>
                  setQuestion(
                    event
                      .target
                      .value,
                  )
                }

                placeholder="Ask TraceGraph a question..."

                rows={3}

                disabled={
                  loading
                }

                className="min-h-28 w-full resize-none bg-transparent px-4 py-4 text-base text-white outline-none placeholder:text-zinc-600"
              />

              <div className="flex items-center justify-between border-t border-white/[0.07] px-2 pt-3">
                <div className="hidden items-center gap-2 text-xs text-zinc-600 sm:flex">
                  <span>
                    GraphRAG
                  </span>

                  <span>
                    •
                  </span>

                  <span>
                    Hybrid Search
                  </span>

                  <span>
                    •
                  </span>

                  <span>
                    Verified
                  </span>
                </div>

                <button
                  type="submit"

                  disabled={
                    loading ||
                    !question.trim() ||
                    apiStatus ===
                      "offline"
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
                  questions={
                    exampleQuestions
                  }

                  onQuestion={
                    submitQuestion
                  }
                />
              )}

            {loading && (
              <LoadingState
                scopeLabel={
                  scopeLabel
                }
                events={streamEvents}
                onStop={() => streamController.current?.abort()}
              />
            )}

            {error && (
              <ErrorState
                message={
                  error
                }
              />
            )}

            {result && (
              <TraceGraphResult
                result={
                  result
                }

                documents={
                  documents
                }
              />
            )}
          </div>
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
    checking:
      "Connecting",

    healthy:
      "System online",

    offline:
      "API offline",
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
            apiStatus ===
            "healthy"
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


function DocumentManager({
  documents,
  loading,
  error,
  selectedDocumentIds,
  uploadLoading,
  uploadError,
  uploadMessage,
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

  apiOnline: boolean;

  onToggleDocument:
    (
      documentId: string,
    ) => void;

  onClearScope:
    () => void;

  onRefresh:
    () => void;

  onUpload:
    (
      file: File,
    ) => Promise<void>;
}) {
  const fileInputRef =
    useRef<HTMLInputElement | null>(
      null,
    );


  const handleFileChange =
    (
      event:
        ChangeEvent<HTMLInputElement>,
    ) => {
      const file =
        event.target.files?.[0];

      if (file) {
        void onUpload(
          file,
        );
      }

      event.target.value =
        "";
    };


  return (
    <aside className="lg:sticky lg:top-6">
      <div className="overflow-hidden rounded-3xl border border-white/[0.08] bg-white/[0.025] shadow-xl shadow-black/20 backdrop-blur-xl">
        <div className="border-b border-white/[0.07] p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-zinc-200">
                Documents
              </p>

              <p className="mt-1 text-xs text-zinc-600">
                Control retrieval
                scope
              </p>
            </div>

            <button
              type="button"

              onClick={
                onRefresh
              }

              disabled={
                loading
              }

              className="rounded-lg border border-white/[0.07] bg-white/[0.025] px-2.5 py-1.5 text-[10px] uppercase tracking-[0.12em] text-zinc-600 transition hover:border-white/15 hover:text-zinc-400 disabled:opacity-40"
            >
              Refresh
            </button>
          </div>

          <button
            type="button"

            onClick={
              onClearScope
            }

            className={`mt-4 w-full rounded-xl border p-3 text-left transition ${
              selectedDocumentIds
                .length === 0
                ? "border-violet-400/20 bg-violet-500/[0.07]"
                : "border-white/[0.06] bg-black/20 hover:border-white/10"
            }`}
          >
            <div className="flex items-center gap-3">
              <SelectionIndicator
                selected={
                  selectedDocumentIds
                    .length === 0
                }
              />

              <div className="min-w-0">
                <p className="text-xs font-medium text-zinc-300">
                  All indexed
                  documents
                </p>

                <p className="mt-1 text-[10px] text-zinc-600">
                  Search the complete
                  knowledge base
                </p>
              </div>
            </div>
          </button>
        </div>

        <div className="max-h-[520px] overflow-y-auto p-3">
          {loading && (
            <DocumentLoadingState />
          )}

          {!loading &&
            error && (
              <div className="rounded-xl border border-red-500/15 bg-red-500/[0.04] p-4">
                <p className="text-xs leading-5 text-red-300/70">
                  {error}
                </p>
              </div>
            )}

          {!loading &&
            !error &&
            documents.length ===
              0 && (
              <div className="px-3 py-8 text-center">
                <p className="text-xs text-zinc-500">
                  No documents
                  indexed yet.
                </p>

                <p className="mt-2 text-[10px] leading-4 text-zinc-700">
                  Upload a PDF,
                  TXT, or Markdown
                  document.
                </p>
              </div>
            )}

          {!loading &&
            !error &&
            documents.map(
              (document) => {
                const selected =
                  selectedDocumentIds.includes(
                    document
                      .document_id,
                  );

                return (
                  <button
                    key={
                      document.document_id
                    }

                    type="button"

                    aria-pressed={
                      selected
                    }

                    onClick={() =>
                      onToggleDocument(
                        document
                          .document_id,
                      )
                    }

                    className={`mb-2 w-full rounded-2xl border p-4 text-left transition last:mb-0 ${
                      selected
                        ? "border-violet-400/20 bg-violet-500/[0.06]"
                        : "border-white/[0.055] bg-black/20 hover:border-white/10 hover:bg-white/[0.025]"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <SelectionIndicator
                        selected={
                          selected
                        }
                      />

                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <p className="truncate text-xs font-medium text-zinc-300">
                            {
                              document.filename
                            }
                          </p>

                          <span className="shrink-0 font-mono text-[9px] uppercase text-zinc-700">
                            {
                              document.file_type
                            }
                          </span>
                        </div>

                        <div className="mt-2">
                          <OntologyBadge
                            profile={
                              document.ontology_profile
                            }
                          />
                        </div>

                        <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-zinc-600">
                          <span>
                            {
                              document.chunk_count
                            }{" "}
                            chunks
                          </span>

                          <span>
                            {
                              document.entity_count
                            }{" "}
                            entities
                          </span>

                          <span>
                            {
                              document.graph_relationship_count
                            }{" "}
                            relationships
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                );
              },
            )}
        </div>

        <div className="border-t border-white/[0.07] p-4">
          <input
            ref={
              fileInputRef
            }

            type="file"

            accept=".pdf,.txt,.md,.markdown"

            className="hidden"

            onChange={
              handleFileChange
            }
          />

          <button
            type="button"

            disabled={
              uploadLoading ||
              !apiOnline
            }

            onClick={() =>
              fileInputRef.current?.click()
            }

            className="w-full rounded-xl border border-white/[0.08] bg-white/[0.035] px-4 py-3 text-xs font-medium text-zinc-400 transition hover:border-violet-400/20 hover:bg-violet-500/[0.05] hover:text-violet-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {uploadLoading
              ? "Indexing document..."
              : "+ Upload document"}
          </button>

          {uploadLoading && (
            <p className="mt-3 text-center text-[10px] leading-4 text-zinc-600">
              Contextual retrieval,
              embeddings, ontology
              detection, and graph
              extraction are running.
            </p>
          )}

          {uploadMessage && (
            <p className="mt-3 text-[10px] leading-4 text-emerald-400/70">
              ✓ {uploadMessage}
            </p>
          )}

          {uploadError && (
            <p className="mt-3 text-[10px] leading-4 text-red-300/70">
              {uploadError}
            </p>
          )}
        </div>
      </div>
    </aside>
  );
}


function SelectionIndicator({
  selected,
}: {
  selected: boolean;
}) {
  return (
    <span
      className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[9px] ${
        selected
          ? "border-violet-400/40 bg-violet-400/15 text-violet-300"
          : "border-zinc-700 bg-black/40 text-transparent"
      }`}
    >
      ✓
    </span>
  );
}


function DocumentLoadingState() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map(
        (item) => (
          <div
            key={
              item
            }

            className="animate-pulse rounded-2xl border border-white/[0.05] bg-black/20 p-4"
          >
            <div className="h-3 w-2/3 rounded bg-zinc-800" />

            <div className="mt-3 h-5 w-24 rounded-full bg-zinc-900" />

            <div className="mt-3 h-2 w-full rounded bg-zinc-900" />
          </div>
        ),
      )}
    </div>
  );
}


function ScopeBar({
  selectedDocuments,
  documentCount,
  scopeLabel,
}: {
  selectedDocuments:
    DocumentSummary[];

  documentCount: number;

  scopeLabel: string;
}) {
  const scoped =
    selectedDocuments.length >
    0;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.02] px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <span
          className={`h-2 w-2 shrink-0 rounded-full ${
            scoped
              ? "bg-violet-400"
              : "bg-blue-400"
          }`}
        />

        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.14em] text-zinc-700">
            Retrieval scope
          </p>

          <p className="mt-0.5 truncate text-xs text-zinc-400">
            {scopeLabel}
          </p>
        </div>
      </div>

      <span className="rounded-lg border border-white/[0.06] bg-black/20 px-2.5 py-1.5 text-[10px] text-zinc-600">
        {scoped
          ? "Scoped retrieval"
          : `${documentCount} indexed`}
      </span>
    </div>
  );
}


function OntologyBadge({
  profile,
}: {
  profile:
    | string
    | null;
}) {
  const label =
    formatOntology(
      profile,
    );

  const className =
    ontologyBadgeClass(
      profile,
    );

  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[9px] font-medium uppercase tracking-[0.11em] ${className}`}
    >
      {label}
    </span>
  );
}


function formatOntology(
  profile:
    | string
    | null,
): string {
  if (!profile) {
    return "General";
  }

  return profile
    .split("+")
    .map(
      (item) =>
        item
          .charAt(0)
          .toUpperCase() +
        item.slice(1),
    )
    .join(" + ");
}


function ontologyBadgeClass(
  profile:
    | string
    | null,
): string {
  switch (profile) {
    case "research":
      return "border-blue-400/20 bg-blue-500/[0.07] text-blue-300";

    case "career":
      return "border-emerald-400/20 bg-emerald-500/[0.07] text-emerald-300";

    case "policy":
      return "border-amber-400/20 bg-amber-500/[0.07] text-amber-300";

    case "contract":
      return "border-pink-400/20 bg-pink-500/[0.07] text-pink-300";

    case "policy+contract":
      return "border-violet-400/20 bg-violet-500/[0.08] text-violet-300";

    default:
      return "border-zinc-500/20 bg-zinc-500/[0.07] text-zinc-400";
  }
}


function ExampleQuestions({
  questions,
  onQuestion,
}: {
  questions: string[];

  onQuestion:
    (
      question: string,
    ) => Promise<void>;
}) {
  return (
    <div className="mt-7">
      <p className="mb-3 text-xs uppercase tracking-[0.16em] text-zinc-700">
        Try an example
      </p>

      <div className="grid gap-2 sm:grid-cols-2">
        {questions.map(
          (item) => (
            <button
              key={
                item
              }

              type="button"

              onClick={() =>
                void onQuestion(
                  item,
                )
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


function LoadingState({
  scopeLabel,
  events,
  onStop,
}: {
  scopeLabel: string;
  events: ChatStreamEvent[];
  onStop: () => void;
}) {
  const visible = events.filter((event) => event.type !== "completed");
  return (
    <section className="mt-8 rounded-3xl border border-white/[0.08] bg-white/[0.025] p-6" aria-live="polite" aria-label="Live TraceGraph execution">
      <div className="flex items-center gap-3">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-violet-400" />

        <div className="min-w-0 flex-1">
          <span className="text-sm text-zinc-300">Live execution</span>

          <p className="mt-1 text-[10px] text-zinc-700">
            Scope:{" "}
            {scopeLabel}
          </p>
        </div>
        <button type="button" onClick={onStop} className="rounded-lg border border-white/[0.09] px-3 py-2 text-xs text-zinc-400 hover:border-white/20 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400">Stop</button>
      </div>

      <div className="mt-6 space-y-2">
        {visible.map((event, index) => (
          <div key={`${event.type}-${event.id ?? index}-${event.status}`} className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-black/20 p-3">
            <span className={event.status === "complete" ? "text-emerald-400" : event.status === "limited" ? "text-amber-400" : "animate-pulse text-violet-400"}>{event.status === "complete" ? "✓" : event.status === "limited" ? "!" : "●"}</span>
            <div className="min-w-0"><p className="text-xs font-medium text-zinc-300">{event.id ? `${event.id} · ` : ""}{titleCase(event.type)}{event.route ? ` · ${titleCase(event.route)}` : ""}</p><p className="mt-1 text-[11px] leading-5 text-zinc-600">{event.message}</p></div>
          </div>
        ))}
        {visible.length === 0 && <p className="text-xs text-zinc-600">Connecting to TraceGraph…</p>}
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
        TraceGraph request
        failed
      </p>

      <p className="mt-2 text-sm text-red-300/60">
        {message}
      </p>
    </section>
  );
}


function TraceGraphResult({ result, documents }: { result: TraceGraphResponse; documents: DocumentSummary[] }) {
  const [selectedEvidence, setSelectedEvidence] = useState<TraceGraphEvidence | null>(null);
  const [showMetrics, setShowMetrics] = useState(false);
  const scopeNames = result.document_ids?.map((id) => documents.find((doc) => doc.document_id === id)?.filename ?? id) ?? [];
  const citedLabels = new Set(result.used_evidence_labels.map((label) => label.replace(/^\[|\]$/g, "")));
  const cited = result.evidence_items.filter((item) => citedLabels.has(item.label));
  const evidence = cited.length ? cited : result.evidence_items;
  const graphEvidence = evidence.filter((item) => item.kind === "graph" && item.graph_fact);

  return <section className="mt-8 space-y-4" aria-label="TraceGraph answer and evidence">
    <div className="rounded-3xl border border-white/[0.09] bg-[#0a0a0a] p-6 shadow-2xl shadow-black/40 md:p-8">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={result.answer_status} />
        <span className="rounded-full border border-white/[0.07] px-3 py-1 text-[11px] text-zinc-500">{scopeNames.length ? `${scopeNames.length} scoped document${scopeNames.length === 1 ? "" : "s"}` : "All documents"}</span>
      </div>
      {scopeNames.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{scopeNames.map((name) => <span key={name} className="rounded-lg bg-violet-500/[0.04] px-2.5 py-1.5 text-[10px] text-violet-300/70">{name}</span>)}</div>}
      <p className="mt-7 text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-300/70">Answer</p>
      <MarkdownAnswer value={result.answer} />
      {evidence.length > 0 && <div className="mt-7 flex flex-wrap gap-2" aria-label="Answer evidence">{evidence.map((item) => <button key={item.label} type="button" onClick={() => setSelectedEvidence(item)} className="rounded-lg border border-violet-400/15 bg-violet-500/[0.05] px-3 py-2 font-mono text-[10px] text-violet-200/70 transition hover:border-violet-400/35 hover:text-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400">{item.label}</button>)}</div>}
    </div>

    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-2xl border border-violet-400/15 bg-violet-500/[0.035] p-5 md:p-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-300/60">Routing decision</p>
        <h2 className="mt-3 text-xl font-medium text-zinc-100">{titleCase(result.final_route ?? result.route)} Retrieval</h2>
        <p className="mt-2 text-sm leading-6 text-zinc-400">{result.routing_reason ?? "TraceGraph selected the available grounded evidence."}</p>
        <div className="mt-5 grid grid-cols-2 gap-3"><EvidenceCount label="Hybrid evidence" value={`${result.hybrid_evidence_count} candidates`} /><EvidenceCount label="Graph evidence" value={`${result.graph_evidence_count} facts`} /></div>
        <button type="button" onClick={() => setShowMetrics((value) => !value)} aria-expanded={showMetrics} className="mt-4 rounded text-xs text-zinc-500 underline decoration-zinc-700 underline-offset-4 hover:text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400">{showMetrics ? "Hide technical details" : "Show technical details"}</button>
        {showMetrics && <div className="mt-3 font-mono text-[10px] leading-5 text-zinc-600">Hybrid top: {formatScore(result.hybrid_top_relevance)} · Graph top: {formatScore(result.graph_top_relevance)} · Strategy: {result.strategy}</div>}
      </section>
      <section className="rounded-2xl border border-white/[0.08] bg-[#0a0a0a] p-5 md:p-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600">Execution path</p>
        <div className="mt-5 flex flex-wrap items-center gap-2 text-xs">
          <PipelineNode>{result.strategy === "adaptive_evidence" ? "Adaptive Retrieval" : "Router"}</PipelineNode><Arrow />
          {result.decomposition_used ? <><PipelineNode active>Decomposition</PipelineNode><Arrow /><PipelineNode>Evidence Merge</PipelineNode><Arrow /></> : <><PipelineNode active>{titleCase(result.final_route ?? result.route)}</PipelineNode><Arrow /></>}
          <PipelineNode>Research</PipelineNode><Arrow /><PipelineNode verified={result.verified}>Verification {result.verified ? "✓" : ""}</PipelineNode>
        </div>
        {(result.degraded || result.decomposition_degraded) && <p className="mt-4 rounded-lg border border-amber-400/15 bg-amber-400/[0.04] p-3 text-xs text-amber-200/70">Execution completed with limited evidence{result.degradation_reason ? `: ${result.degradation_reason}` : "."}</p>}
      </section>
    </div>

    {result.decomposition_used && <section className="rounded-2xl border border-white/[0.08] bg-[#0a0a0a] p-5 md:p-6">
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600">Question decomposition</p>
      <div className="mt-5 grid gap-3 md:grid-cols-3">{result.subquestions.map((item, index) => <div key={item.id} className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-4">
        <div className="flex items-center justify-between"><span className="font-mono text-xs text-violet-300">{index + 1}</span><RouteBadge route={item.route ?? "unresolved"} /></div>
        <p className="mt-3 text-sm leading-6 text-zinc-300">{item.question}</p><p className="mt-3 text-xs text-zinc-600">{item.evidence_count} evidence items{item.depends_on?.length ? ` · after ${item.depends_on.join(", ")}` : ""}</p>
      </div>)}</div>
    </section>}

    {graphEvidence.length > 0 && <section className="rounded-2xl border border-white/[0.08] bg-[#0a0a0a] p-5 md:p-6">
      <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600">Graph evidence</p>
      <div className="mt-5 grid gap-3 xl:grid-cols-2">{graphEvidence.map((item) => <GraphEvidenceCard key={item.label} evidence={item} onOpen={() => setSelectedEvidence(item)} />)}</div>
    </section>}
    {result.verification_reason && <details className="rounded-2xl border border-white/[0.07] bg-[#0a0a0a] p-5 text-sm text-zinc-500"><summary className="cursor-pointer text-xs font-medium text-zinc-400">Verification report</summary><p className="mt-3 leading-6">{result.verification_reason}</p></details>}
    {selectedEvidence && <EvidenceDrawer evidence={selectedEvidence} onClose={() => setSelectedEvidence(null)} />}
  </section>;
}

function LegacyTraceGraphResult({
  result,
  documents,
}: {
  result: TraceGraphResponse;

  documents: DocumentSummary[];
}) {
  const scopeNames =
    result.document_ids
      ?.map(
        (documentId) =>
          documents.find(
            (document) =>
              document.document_id ===
              documentId,
          )?.filename ??
          documentId,
      ) ?? [];

  return (
    <section className="mt-8 overflow-hidden rounded-3xl border border-white/[0.09] bg-[#0a0a0a] shadow-2xl shadow-black/40">
      <div className="border-b border-white/[0.07] p-6 md:p-7">
        <div className="flex flex-wrap items-center gap-2">
          <RouteBadge
            route={
              result.route
            }
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

          <span className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-1 text-[11px] text-zinc-500">
            {scopeNames.length >
            0
              ? `${scopeNames.length} scoped document${
                  scopeNames.length ===
                  1
                    ? ""
                    : "s"
                }`
              : "All documents"}
          </span>
        </div>

        {scopeNames.length >
          0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {scopeNames.map(
              (name) => (
                <span
                  key={
                    name
                  }

                  className="rounded-lg border border-violet-400/10 bg-violet-500/[0.035] px-2.5 py-1.5 text-[10px] text-violet-300/70"
                >
                  {name}
                </span>
              ),
            )}
          </div>
        )}

        <p className="mt-6 whitespace-pre-wrap text-[15px] leading-7 text-zinc-200 md:text-base">
          {result.answer}
        </p>

        {result
          .used_evidence_labels
          .length > 0 && (
          <div className="mt-6 flex flex-wrap gap-2">
            {result.used_evidence_labels.map(
              (
                label,
              ) => (
                <span
                  key={
                    label
                  }

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

          <PipelineNode
            active
          >
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
              Verification
              report
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

        {result
          .retrieved_chunk_ids
          .length > 0 && (
          <div className="mt-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
            <p className="text-[10px] uppercase tracking-[0.15em] text-zinc-700">
              Retrieved chunks
            </p>

            <p className="mt-2 font-mono text-[10px] leading-5 text-zinc-600">
              {result
                .retrieved_chunk_ids
                .join(
                  " · ",
                )}
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
  children: ReactNode;

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

void LegacyTraceGraphResult;

function titleCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function formatScore(value: number | null) {
  return value === null ? "Unavailable" : value.toFixed(3);
}

function StatusBadge({ status }: { status: TraceGraphResponse["answer_status"] }) {
  const labels = {
    verified_answer: ["Verified answer", "border-emerald-500/20 bg-emerald-500/[0.07] text-emerald-300"],
    verified_abstention: ["Verified grounded abstention", "border-sky-500/20 bg-sky-500/[0.07] text-sky-300"],
    degraded_retrieval: ["Degraded retrieval", "border-amber-500/20 bg-amber-500/[0.07] text-amber-300"],
    partial_grounded_answer: ["Partial grounded answer", "border-amber-500/20 bg-amber-500/[0.07] text-amber-300"],
    grounded_abstention: ["Grounded abstention", "border-zinc-500/20 bg-zinc-500/[0.07] text-zinc-300"],
  } as const;
  const [label, style] = labels[status];
  return <span className={`rounded-full border px-3 py-1 text-[11px] font-medium ${style}`}>{label}</span>;
}

function EvidenceCount({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-white/[0.06] bg-black/20 p-3"><p className="text-[10px] text-zinc-600">{label}</p><p className="mt-1 text-sm text-zinc-300">{value}</p></div>;
}

function InlineMarkdown({ value }: { value: string }) {
  return <>{value.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index} className="rounded bg-white/[0.07] px-1.5 py-0.5 font-mono text-[0.9em] text-violet-200">{part.slice(1, -1)}</code>;
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index} className="font-semibold text-zinc-100">{part.slice(2, -2)}</strong>;
    return <span key={index}>{part}</span>;
  })}</>;
}

function MarkdownAnswer({ value }: { value: string }) {
  const nodes: ReactNode[] = [];
  const lines = value.replace(/<[^>]*>/g, "").split("\n");
  for (let index = 0; index < lines.length;) {
    const line = lines[index].trim();
    if (!line) { index += 1; continue; }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) { nodes.push(<h3 key={index} className="mt-6 text-lg font-semibold text-zinc-100"><InlineMarkdown value={heading[2]} /></h3>); index += 1; continue; }
    const unordered = line.match(/^[-*]\s+(.+)$/);
    if (unordered) {
      const items = []; const start = index;
      while (index < lines.length) { const match = lines[index].trim().match(/^[-*]\s+(.+)$/); if (!match) break; items.push(match[1]); index += 1; }
      nodes.push(<ul key={start} className="mt-4 list-disc space-y-2 pl-5 text-zinc-300">{items.map((item, itemIndex) => <li key={itemIndex}><InlineMarkdown value={item} /></li>)}</ul>); continue;
    }
    const ordered = line.match(/^\d+[.)]\s+(.+)$/);
    if (ordered) {
      const items = []; const start = index;
      while (index < lines.length) { const match = lines[index].trim().match(/^\d+[.)]\s+(.+)$/); if (!match) break; items.push(match[1]); index += 1; }
      nodes.push(<ol key={start} className="mt-4 list-decimal space-y-2 pl-5 text-zinc-300">{items.map((item, itemIndex) => <li key={itemIndex}><InlineMarkdown value={item} /></li>)}</ol>); continue;
    }
    nodes.push(<p key={index} className="mt-4 text-[15px] leading-7 text-zinc-200 md:text-base"><InlineMarkdown value={line} /></p>); index += 1;
  }
  return <div>{nodes}</div>;
}

function GraphEvidenceCard({ evidence, onOpen }: { evidence: TraceGraphEvidence; onOpen: () => void }) {
  const fact = evidence.graph_fact!;
  return <button type="button" onClick={onOpen} aria-label={`Open source for ${fact.source} ${fact.relationship} ${fact.target}`} className="group w-full rounded-xl border border-white/[0.07] bg-white/[0.02] p-4 text-left transition hover:border-violet-400/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400">
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 text-center">
      <span className="break-words rounded-lg bg-violet-500/[0.07] px-3 py-3 text-sm text-violet-100">{fact.source}</span>
      <span className="max-w-32 break-words font-mono text-[9px] text-violet-300/70"><span className="block text-zinc-700">→</span>{fact.relationship}<span className="block text-zinc-700">→</span></span>
      <span className="break-words rounded-lg bg-white/[0.04] px-3 py-3 text-sm text-zinc-200">{fact.target}</span>
    </div>
    <p className="mt-3 truncate text-[10px] text-zinc-600">{evidence.filename ?? "Indexed document"}{evidence.page_number !== null ? ` · Page ${evidence.page_number}` : ""} · View provenance</p>
  </button>;
}

function EvidenceDrawer({ evidence, onClose }: { evidence: TraceGraphEvidence; onClose: () => void }) {
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose]);
  return <div className="fixed inset-0 z-50 flex justify-end bg-black/70 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}>
    <aside role="dialog" aria-modal="true" aria-labelledby="evidence-title" className="h-full w-full max-w-lg overflow-y-auto border-l border-white/[0.1] bg-[#090909] p-6 shadow-2xl md:p-8">
      <div className="flex items-start justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[0.2em] text-violet-300/60">{evidence.kind === "graph" ? "Source graph fact" : "Source evidence"}</p><h2 id="evidence-title" className="mt-2 text-lg font-medium text-zinc-100">{evidence.filename ?? "Indexed document"}</h2></div><button type="button" onClick={onClose} aria-label="Close evidence drawer" autoFocus className="rounded-lg border border-white/[0.08] px-3 py-2 text-sm text-zinc-400 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400">Close</button></div>
      <div className="mt-6 flex flex-wrap gap-2 text-[10px] text-zinc-500">{evidence.page_number !== null && <span>Page {evidence.page_number}</span>}<span>{titleCase(evidence.retrieval_route)} retrieval</span>{evidence.chunk_id && <span className="font-mono">Chunk {evidence.chunk_id.slice(0, 12)}…</span>}</div>
      {evidence.graph_fact && <div className="mt-6 rounded-xl border border-violet-400/15 bg-violet-500/[0.04] p-4"><p className="text-sm text-zinc-200">{evidence.graph_fact.source}</p><p className="my-2 font-mono text-xs text-violet-300">{evidence.graph_fact.relationship} →</p><p className="text-sm text-zinc-200">{evidence.graph_fact.target}</p></div>}
      <div className="mt-6 border-t border-white/[0.07] pt-6"><p className="whitespace-pre-wrap text-sm leading-7 text-zinc-300">{evidence.text || "No source excerpt was returned for this evidence item."}</p></div>
      {evidence.subquestion && <div className="mt-6 border-t border-white/[0.07] pt-6"><p className="text-[10px] uppercase tracking-[0.15em] text-zinc-600">Used for</p><p className="mt-2 text-sm leading-6 text-zinc-400">“{evidence.subquestion}”</p></div>}
    </aside>
  </div>;
}
