from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TraceGraph AI"
    app_env: str = "development"
    debug: bool = True

    frontend_url: str = "http://localhost:3000"

    # Gemini
    gemini_api_key: str | None = None
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768


    generation_model: str = "gemini-3.6-flash"
    contextualization_model: str = "gemini-3.5-flash-lite"

    # Qdrant
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "tracegraph_chunks"
    qdrant_contextual_collection: str = "tracegraph_chunks_contextual"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()