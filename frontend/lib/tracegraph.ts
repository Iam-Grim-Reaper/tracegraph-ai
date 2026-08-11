export type RetrievalRoute =
  | "hybrid"
  | "graph"
  | "fused";

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
}

export interface TraceGraphRequest {
  question: string;
}

interface ApiErrorResponse {
  detail?: string;
}

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";


export async function askTraceGraph(
  question: string,
): Promise<TraceGraphResponse> {
  const trimmedQuestion = question.trim();

  if (!trimmedQuestion) {
    throw new Error(
      "Question cannot be empty.",
    );
  }

  const response = await fetch(
    `${API_URL}/api/chat`,
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        question: trimmedQuestion,
      } satisfies TraceGraphRequest),
    },
  );

  if (!response.ok) {
    let message =
      "TraceGraph could not answer the question.";

    try {
      const errorBody =
        (await response.json()) as ApiErrorResponse;

      if (
        typeof errorBody.detail ===
        "string"
      ) {
        message = errorBody.detail;
      }
    } catch {
      // If the backend response is not JSON,
      // keep the default error message.
    }

    throw new Error(
      message
    );
  }

  const data =
    (await response.json()) as TraceGraphResponse;

  return data;
}