"use client";

import { useEffect, useState } from "react";

type ApiStatus = "checking" | "healthy" | "offline";

type HealthResponse = {
  status: string;
  service: string;
};

export default function Home() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    const checkApi = async () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;

      if (!apiUrl) {
        setApiStatus("offline");
        return;
      }

      try {
        const response = await fetch(`${apiUrl}/health`);

        if (!response.ok) {
          throw new Error("API health check failed");
        }

        const data = (await response.json()) as HealthResponse;

        setApiStatus(
          data.status === "healthy" ? "healthy" : "offline"
        );
      } catch (error) {
        console.error("TraceGraph API connection failed:", error);
        setApiStatus("offline");
      }
    };

    checkApi();
  }, []);

  const apiLabel: Record<ApiStatus, string> = {
    checking: "Checking...",
    healthy: "Healthy",
    offline: "Offline",
  };

  const apiIndicator: Record<ApiStatus, string> = {
    checking: "●",
    healthy: "●",
    offline: "●",
  };

  return (
    <main className="min-h-screen bg-black text-white">
      <div className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6">
        <div className="mb-12">
          <p className="mb-3 text-sm uppercase tracking-[0.3em] text-gray-500">
            Context-Aware Agentic GraphRAG
          </p>

          <h1 className="text-5xl font-semibold tracking-tight">
            TraceGraph AI
          </h1>

          <p className="mt-4 max-w-2xl text-lg text-gray-400">
            An explainable retrieval and reasoning platform combining
            contextual retrieval, hybrid search, knowledge graphs,
            and agentic verification.
          </p>
        </div>

        <section className="rounded-2xl border border-gray-800 bg-gray-950 p-8">
          <div className="mb-6">
            <h2 className="text-xl font-medium">System Status</h2>
            <p className="mt-1 text-sm text-gray-500">
              TraceGraph infrastructure readiness
            </p>
          </div>

          <div className="space-y-5">
            <StatusRow
              name="Frontend"
              status="Online"
              indicator="●"
            />

            <StatusRow
              name="API"
              status={apiLabel[apiStatus]}
              indicator={apiIndicator[apiStatus]}
            />

            <StatusRow
              name="Knowledge Graph"
              status="Not configured"
              indicator="○"
            />

            <StatusRow
              name="Vector Retrieval"
              status="Not configured"
              indicator="○"
            />

            <StatusRow
              name="LLM"
              status="Not configured"
              indicator="○"
            />
          </div>
        </section>

        <p className="mt-8 text-sm text-gray-600">
          TraceGraph AI · Development Environment
        </p>
      </div>
    </main>
  );
}

function StatusRow({
  name,
  status,
  indicator,
}: {
  name: string;
  status: string;
  indicator: string;
}) {
  return (
    <div className="flex items-center justify-between border-b border-gray-900 pb-4 last:border-none last:pb-0">
      <div className="flex items-center gap-3">
        <span>{indicator}</span>
        <span className="text-gray-300">{name}</span>
      </div>

      <span className="text-sm text-gray-500">{status}</span>
    </div>
  );
}