from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MAX Neural Afisha"
    app_env: str = "development"
    app_version: str = "v4-thresholded-fallback"
    debug: bool = True

    database_url: str = (
        "postgresql+asyncpg://max_afisha:max_afisha@postgres:5432/max_afisha"
    )

    max_bot_token: str = ""
    max_bot_name: str = ""
    max_webhook_secret: str = ""
    admin_token: str = "change-me-local-admin"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    auto_embed_after_ingest: bool = True
    parser_service_url: str = "http://parser:8010"

    text_encoder_model: str = "intfloat/multilingual-e5-small"
    text_encoder_device: str = "cpu"
    text_encoder_batch_size: int = 32
    model_version: str = "retrieval-v1-e5"

    # Relevance gates: weak semantic matches must never be presented as
    # personalized recommendations. Values are configurable for calibration.
    recommendation_min_semantic_similarity: float = 0.78
    recommendation_min_final_score: float = 0.62
    neural_search_min_similarity: float = 0.78

    # MAX Mini App initData is short-lived. One hour is the platform-recommended
    # freshness window used by this MVP.
    max_init_data_max_age_seconds: int = 3600

    source_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152 Safari/537.36"
    )
    source_timeout_seconds: float = 20.0
    source_request_delay_seconds: float = 0.35
    source_max_detail_pages: int = 40

    afisha_ru_enabled: bool = True
    yandex_afisha_enabled: bool = True
    demo_source_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
