from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TraceGraph AI"
    app_env: str = "development"
    debug: bool = True

    graph_extraction_cache_dir: Path = Path(
        ".cache/graph_extractions"
    )

    # Query Intelligence V2. ``legacy`` preserves the
    # regex router as an explicit rollback path.
    query_routing_mode: str = "adaptive"

    # Initial engineering defaults for deciding whether
    # CrossEncoder-ranked evidence is usable. These are
    # configurable deployment controls, not calibrated
    # confidence claims.
    adaptive_evidence_relevance_threshold: float = -9.0
    adaptive_evidence_dominance_margin: float = 2.0
    adaptive_evidence_mean_top_k: int = 3
    adaptive_graph_max_seed_entities: int = 5
    adaptive_graph_max_facts: int = 20
    adaptive_hybrid_candidate_limit: int = 30
    adaptive_hybrid_limit: int = 15
    reranker_model_name: str = (
        "cross-encoder/ms-marco-MiniLM-L6-v2"
    )
    decomposition_model: str = "gemini-3.5-flash-lite"
    decomposition_max_subquestions: int = 3

    office_max_archive_uncompressed_bytes: int = 100 * 1024 * 1024
    office_max_archive_entries: int = 5000
    xlsx_max_worksheets: int = 20
    xlsx_max_rows_per_sheet: int = 5000
    xlsx_max_columns: int = 100
    xlsx_max_non_empty_cells: int = 100000
    office_max_extracted_chars: int = 2_000_000

    frontend_url: str = "http://localhost:3000"

    # Gemini
    gemini_api_key: str | None = None
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768


    generation_model: str = "gemini-3.6-flash"
    contextualization_model: str = "gemini-3.5-flash-lite"

    graph_extraction_model: str = (
    "gemini-3.5-flash-lite"
    )

    provider_max_attempts: int = 3
    provider_default_timeout_seconds: float = 60.0
    provider_long_timeout_seconds: float = 120.0
    provider_retry_base_delay_seconds: float = 0.5
    provider_retry_max_delay_seconds: float = 2.0


    # Qdrant
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "tracegraph_chunks"
    qdrant_contextual_collection: str = "tracegraph_chunks_contextual"
    qdrant_hybrid_collection: str = "tracegraph_chunks_hybrid"

    # Neo4j
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None
    neo4j_database: str = "neo4j"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
