export type RetrievalRoute =
  | "hybrid"
  | "graph"
  | "fused";


export type OntologyMethod =
  | "deterministic"
  | "llm"
  | "fallback"
  | "explicit";


export interface DocumentSummary {
  document_id: string;

  filename: string;

  file_type: string;

  title: string | null;

  author: string | null;

  ontology_profile: string | null;

  ontology_version: string | null;

  ontology_profiles: string[];

  ontology_confidence: number | null;

  ontology_method:
    | OntologyMethod
    | null;

  ontology_reason: string | null;

  ontology_scores: Record<
    string,
    number
  >;

  chunk_count: number;

  entity_count: number;

  graph_relationship_count: number;

  status: "ready";
}


export interface DocumentUploadResponse
  extends DocumentSummary {
  qdrant_indexed_chunks: number;

  graph_rejected_relationship_count: number;

  graph_cached_chunks: number;

  graph_extracted_chunks: number;
}


export interface DocumentListResponse {
  documents: DocumentSummary[];

  total: number;
}


export interface TraceGraphResponse {
  answer: string;

  route: RetrievalRoute;

  verified: boolean;

  verification_reason: string | null;

  retry_count: number;

  rewritten_question: string | null;

  retrieved_chunk_ids: string[];

  graph_fact_count: number;

  used_evidence_labels: string[];

  document_ids: string[] | null;
}


export interface TraceGraphRequest {
  question: string;

  document_ids?: string[];
}


interface ApiErrorResponse {
  detail?: string;
}


export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";


async function readApiError(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body =
      (await response.json()) as ApiErrorResponse;

    if (
      typeof body.detail === "string" &&
      body.detail.trim()
    ) {
      return body.detail;
    }
  } catch {
    // Keep the supplied fallback when the
    // backend does not return JSON.
  }

  return fallback;
}


function normalizeDocumentIds(
  documentIds?: string[],
): string[] {
  if (!documentIds) {
    return [];
  }

  return Array.from(
    new Set(
      documentIds
        .map((documentId) =>
          documentId.trim(),
        )
        .filter(Boolean),
    ),
  );
}


export async function askTraceGraph(
  question: string,
  documentIds?: string[],
): Promise<TraceGraphResponse> {
  const trimmedQuestion =
    question.trim();

  if (!trimmedQuestion) {
    throw new Error(
      "Question cannot be empty.",
    );
  }

  const normalizedDocumentIds =
    normalizeDocumentIds(
      documentIds,
    );

  const requestBody: TraceGraphRequest = {
    question: trimmedQuestion,
  };

  if (
    normalizedDocumentIds.length > 0
  ) {
    requestBody.document_ids =
      normalizedDocumentIds;
  }

  const response = await fetch(
    `${API_URL}/api/chat`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify(
        requestBody,
      ),
    },
  );

  if (!response.ok) {
    const message =
      await readApiError(
        response,
        "TraceGraph could not answer the question.",
      );

    throw new Error(
      message,
    );
  }

  return (
    (await response.json()) as TraceGraphResponse
  );
}


export async function getDocuments():
Promise<DocumentListResponse> {
  const response = await fetch(
    `${API_URL}/api/documents`,
    {
      method: "GET",

      cache: "no-store",
    },
  );

  if (!response.ok) {
    const message =
      await readApiError(
        response,
        "TraceGraph could not load indexed documents.",
      );

    throw new Error(
      message,
    );
  }

  return (
    (await response.json()) as DocumentListResponse
  );
}


export async function getDocument(
  documentId: string,
): Promise<DocumentSummary> {
  const normalizedId =
    documentId.trim();

  if (!normalizedId) {
    throw new Error(
      "Document ID cannot be empty.",
    );
  }

  const response = await fetch(
    `${API_URL}/api/documents/${encodeURIComponent(
      normalizedId,
    )}`,
    {
      method: "GET",

      cache: "no-store",
    },
  );

  if (!response.ok) {
    const message =
      await readApiError(
        response,
        "TraceGraph could not load the document.",
      );

    throw new Error(
      message,
    );
  }

  return (
    (await response.json()) as DocumentSummary
  );
}


export async function uploadDocument(
  file: File,
): Promise<DocumentUploadResponse> {
  if (!file) {
    throw new Error(
      "Select a document to upload.",
    );
  }

  const formData =
    new FormData();

  formData.append(
    "file",
    file,
  );

  const response = await fetch(
    `${API_URL}/api/documents`,
    {
      method: "POST",

      body: formData,
    },
  );

  if (!response.ok) {
    const message =
      await readApiError(
        response,
        "TraceGraph could not index the document.",
      );

    throw new Error(
      message,
    );
  }

  return (
    (await response.json()) as DocumentUploadResponse
  );
}