from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProductionConfigurationError(RuntimeError):
    """Safe production configuration error containing setting names only."""


class Settings(BaseSettings):
    app_name: str = "TraceGraph AI"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = True

    graph_extraction_cache_dir: Path = Path(
        ".cache/graph_extractions"
    )

    # Query Intelligence V2. ``legacy`` preserves the
    # regex router as an explicit rollback path.
    query_routing_mode: Literal["adaptive", "legacy"] = "adaptive"

    # Initial engineering defaults for deciding whether
    # CrossEncoder-ranked evidence is usable. These are
    # configurable deployment controls, not calibrated
    # confidence claims.
    adaptive_evidence_relevance_threshold: float = -9.0
    adaptive_evidence_dominance_margin: float = 2.0
    adaptive_evidence_mean_top_k: int = Field(default=3, gt=0)
    adaptive_graph_max_seed_entities: int = Field(default=5, gt=0)
    adaptive_graph_max_facts: int = Field(default=20, gt=0)
    adaptive_hybrid_candidate_limit: int = Field(default=30, gt=0)
    adaptive_hybrid_limit: int = Field(default=15, gt=0)
    reranker_model_name: str = (
        "cross-encoder/ms-marco-MiniLM-L6-v2"
    )
    decomposition_model: str = "gemini-3.5-flash-lite"
    decomposition_max_subquestions: int = Field(default=3, ge=2, le=3)

    office_max_archive_uncompressed_bytes: int = Field(
        default=100 * 1024 * 1024, gt=0
    )
    office_max_archive_entries: int = Field(default=5000, gt=0)
    xlsx_max_worksheets: int = Field(default=20, gt=0)
    xlsx_max_rows_per_sheet: int = Field(default=5000, gt=0)
    xlsx_max_columns: int = Field(default=100, gt=0)
    xlsx_max_non_empty_cells: int = Field(default=100000, gt=0)
    office_max_extracted_chars: int = Field(default=2_000_000, gt=0)

    frontend_url: str = "http://localhost:3000"
    cors_allowed_origins: str | None = None

    # Gemini
    gemini_api_key: str | None = None
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = Field(default=768, gt=0, le=4096)


    generation_model: str = "gemini-3.6-flash"
    contextualization_model: str = "gemini-3.5-flash-lite"

    graph_extraction_model: str = (
    "gemini-3.5-flash-lite"
    )

    provider_max_attempts: int = Field(default=3, ge=1, le=3)
    provider_default_timeout_seconds: float = Field(default=60.0, gt=0)
    provider_long_timeout_seconds: float = Field(default=120.0, gt=0)
    provider_retry_base_delay_seconds: float = Field(default=0.5, ge=0)
    provider_retry_max_delay_seconds: float = Field(default=2.0, ge=0)


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

    @property
    def allowed_cors_origins(self) -> list[str]:
        value = self.cors_allowed_origins
        if value is None:
            return [self.frontend_url.strip()]
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_environment(self):
        explicit_debug = "debug" in self.model_fields_set
        if self.app_env in {"test", "production"} and not explicit_debug:
            object.__setattr__(self, "debug", False)

        if (
            self.provider_retry_max_delay_seconds
            < self.provider_retry_base_delay_seconds
        ):
            raise ValueError(
                "PROVIDER_RETRY_MAX_DELAY_SECONDS must be greater than or "
                "equal to PROVIDER_RETRY_BASE_DELAY_SECONDS"
            )

        if self.app_env != "production":
            return self

        if self.debug:
            raise ProductionConfigurationError(
                "Invalid production setting: DEBUG must be false"
            )

        required = {
            "GEMINI_API_KEY": self.gemini_api_key,
            "QDRANT_URL": self.qdrant_url,
            "QDRANT_API_KEY": self.qdrant_api_key,
            "QDRANT_HYBRID_COLLECTION": self.qdrant_hybrid_collection,
            "NEO4J_URI": self.neo4j_uri,
            "NEO4J_USERNAME": self.neo4j_username,
            "NEO4J_PASSWORD": self.neo4j_password,
            "NEO4J_DATABASE": self.neo4j_database,
            "RERANKER_MODEL_NAME": self.reranker_model_name,
            "CORS_ALLOWED_ORIGINS": self.cors_allowed_origins,
        }
        placeholders = {"change-me", "changeme", "placeholder", "replace-me"}
        for name, value in required.items():
            normalized = str(value or "").strip()
            if not normalized or normalized.casefold() in placeholders:
                raise ProductionConfigurationError(
                    f"Missing required production setting: {name}"
                )

        if "*" in self.allowed_cors_origins:
            raise ProductionConfigurationError(
                "Invalid production setting: CORS_ALLOWED_ORIGINS"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
