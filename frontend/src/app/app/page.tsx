"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  API_URL,
  ChatStreamEvent,
  DocumentSummary,
  getDocuments,
  PUBLIC_UPLOADS_ENABLED,
  TraceGraphResponse,
  streamTraceGraph,
  uploadDocument,
} from "../../../lib/tracegraph";
import {
  AppHeader,
  DocumentRail,
  ErrorState,
  ExampleQuestions,
  LoadingState,
  QuestionComposer,
  TraceGraphResult,
  WorkspaceIntro,
} from "./workspace-ui";

type ApiStatus = "checking" | "healthy" | "offline";

const DOMAIN_QUESTIONS: Record<string, string> = {
  research: "Who developed Grad-CAM?",
  career: "Where did Alex Morgan work and what skills does Alex Morgan have?",
  policy: "What regulation governs the ACME Data Protection Policy?",
  contract: "What obligation does Northstar Analytics LLC have?",
};

const DEFAULT_QUESTIONS = Object.values(DOMAIN_QUESTIONS).slice(0, 3);

export default function Home() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [backendUploadsEnabled, setBackendUploadsEnabled] = useState<boolean | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState<string | null>(null);
  const [result, setResult] = useState<TraceGraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [streamEvents, setStreamEvents] = useState<ChatStreamEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const streamController = useRef<AbortController | null>(null);

  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    setDocumentsError(null);

    try {
      const response = await getDocuments();
      setDocuments(response.documents);
      setBackendUploadsEnabled(response.uploads_enabled);
      const validIds = new Set(response.documents.map((document) => document.document_id));
      setSelectedDocumentIds((current) => current.filter((id) => validIds.has(id)));
    } catch (err) {
      setDocumentsError(err instanceof Error ? err.message : "Unable to load documents.");
    } finally {
      setDocumentsLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialize = async () => {
      try {
        const response = await fetch(`${API_URL}/health`);
        if (!response.ok) {
          throw new Error("API health check failed.");
        }
        const data = (await response.json()) as { status: string };
        setApiStatus(data.status === "healthy" ? "healthy" : "offline");
      } catch {
        setApiStatus("offline");
      }
    };

    void initialize();
    void Promise.resolve().then(loadDocuments);
  }, [loadDocuments]);

  useEffect(() => () => streamController.current?.abort(), []);

  const selectedDocuments = useMemo(
    () => documents.filter((document) => selectedDocumentIds.includes(document.document_id)),
    [documents, selectedDocumentIds],
  );

  const uploadsEnabled =
    PUBLIC_UPLOADS_ENABLED && backendUploadsEnabled === true;

  const scopeLabel = useMemo(() => {
    if (selectedDocuments.length === 0) {
      return "All documents";
    }
    if (selectedDocuments.length === 1) {
      return selectedDocuments[0].filename;
    }
    return `${selectedDocuments.length} selected documents`;
  }, [selectedDocuments]);

  const exampleQuestions = useMemo(() => {
    if (selectedDocuments.length === 0) {
      return DEFAULT_QUESTIONS;
    }

    const profiles = new Set<string>();
    selectedDocuments.forEach((document) => {
      document.ontology_profiles.forEach((profile) => profiles.add(profile));
    });
    const questions = Array.from(profiles)
      .map((profile) => DOMAIN_QUESTIONS[profile])
      .filter((item): item is string => Boolean(item));
    return questions.length > 0 ? questions.slice(0, 3) : DEFAULT_QUESTIONS;
  }, [selectedDocuments]);

  const toggleDocument = (documentId: string) => {
    setSelectedDocumentIds((current) =>
      current.includes(documentId) ? current.filter((id) => id !== documentId) : [...current, documentId],
    );
    setResult(null);
    setError(null);
  };

  const clearDocumentScope = () => {
    setSelectedDocumentIds([]);
    setResult(null);
    setError(null);
  };

  const submitQuestion = async (value?: string) => {
    const finalQuestion = (value ?? question).trim();
    if (!finalQuestion) {
      return;
    }

    setQuestion(finalQuestion);
    setSubmittedQuestion(finalQuestion);
    setLoading(true);
    setError(null);
    setResult(null);
    setStreamEvents([]);
    streamController.current?.abort();
    const controller = new AbortController();
    streamController.current = controller;

    try {
      const response = await streamTraceGraph(
        finalQuestion,
        selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
        (event) => setStreamEvents((current) => [...current, event]),
        controller.signal,
      );
      setResult(response);
    } catch (err) {
      if (controller.signal.aborted) {
        return;
      }
      setError(err instanceof Error ? err.message : "TraceGraph could not process the request.");
    } finally {
      if (streamController.current === controller) {
        setLoading(false);
        streamController.current = null;
      }
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submitQuestion();
  };

  const handleUpload = async (file: File) => {
    if (uploadLoading || !uploadsEnabled) {
      return;
    }
    setUploadLoading(true);
    setUploadError(null);
    setUploadMessage(null);

    try {
      const uploaded = await uploadDocument(file);
      await loadDocuments();
      setSelectedDocumentIds([uploaded.document_id]);
      setUploadMessage(`${uploaded.filename} is indexed and ready to search.`);
      setResult(null);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Document indexing failed.");
    } finally {
      setUploadLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <AppHeader apiStatus={apiStatus} />
      <div className="app-workspace">
        <DocumentRail
          documents={documents}
          loading={documentsLoading}
          error={documentsError}
          selectedDocumentIds={selectedDocumentIds}
          uploadLoading={uploadLoading}
          uploadError={uploadError}
          uploadMessage={uploadMessage}
          uploadsEnabled={uploadsEnabled}
          apiOnline={apiStatus === "healthy"}
          onToggleDocument={toggleDocument}
          onClearScope={clearDocumentScope}
          onRefresh={() => void loadDocuments()}
          onUpload={handleUpload}
        />

        <section className="research-workspace">
          <div className="research-workspace-inner">
            {!result && !loading && !error && <WorkspaceIntro />}
            <QuestionComposer
              question={question}
              scopeLabel={scopeLabel}
              loading={loading}
              apiOffline={apiStatus === "offline"}
              onChange={setQuestion}
              onSubmit={handleSubmit}
            />
            {!result && !loading && !error && (
              <ExampleQuestions questions={exampleQuestions} onQuestion={submitQuestion} />
            )}
            {loading && (
              <LoadingState scopeLabel={scopeLabel} events={streamEvents} onStop={() => streamController.current?.abort()} />
            )}
            {error && <ErrorState message={error} />}
            {result && (
              <TraceGraphResult
                result={result}
                documents={documents}
                question={submittedQuestion ?? question}
                events={streamEvents}
              />
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
