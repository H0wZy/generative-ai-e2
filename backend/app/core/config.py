from pydantic import AnyHttpUrl, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: PostgresDsn

    # Browser calls the API cross-origin from the Next.js dev server. Only
    # local dev ports by default — this API has no auth (see README, "Escopo
    # do MVP"), so it is never meant to sit behind a browser-facing origin
    # other than localhost.
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3100"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    jira_base_url: AnyHttpUrl | None = None
    jira_email: str | None = None
    jira_api_token: SecretStr | None = None

    # One project for every squad. The squad goes on the issue as a label, so a
    # sandbox needs one project instead of one per squad.
    jira_project_key: str | None = None

    # Board that backs the Agile workspace — discovered per Jira instance,
    # never guessed (see research.md R1).
    jira_board_id: int | None = None

    # Freshservice is read by polling — no webhook, so the API is never exposed
    # publicly and there is no signing secret to manage.
    freshservice_domain: str | None = None
    freshservice_api_key: SecretStr | None = None
    freshservice_poll_interval_seconds: int = 30

    # Provider unified on OpenRouter (research.md R2) — evaluators without a
    # local Ollama install can still run the squad classifier. llm_base_url
    # is now vestigial (OpenRouterSquadClient reads assistant_base_url) but
    # stays for OllamaClient, which is not removed yet.
    llm_enabled: bool = False
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    llm_confidence_threshold: float = 0.7
    llm_timeout_seconds: int = 20

    # RAG search service consumed by the assistant (see research.md R6).
    rag_search_url: str = "http://localhost:8100"

    # Assistant — separate namespace from llm_* above. llm_* is the squad
    # classifier via Ollama; assistant_* is the grounded Q&A via OpenRouter.
    # The two models coexist and never share a variable.
    assistant_enabled: bool = False
    assistant_base_url: str = "https://openrouter.ai/api/v1"
    assistant_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    assistant_timeout_seconds: int = 60
    assistant_max_context_chars: int = 12000
    # Teto de tokens de saída — resposta gigante empurra a conversa inteira
    # pra fora da tela (achado de QA exploratório em 2026-07-30).
    assistant_max_tokens: int = 600
    openrouter_api_key: SecretStr | None = None

    # Anexo efêmero por conversa (specs/013) — teto de upload por tipo de
    # arquivo (FR-003) e endpoint/modelo de OCR local via Ollama (FR-011).
    attachment_max_bytes_text: int = 5_000_000
    attachment_max_bytes_pdf: int = 20_000_000
    ocr_base_url: str = "http://localhost:11434"
    ocr_model: str = "frob/unlimited-ocr:f16"

    @property
    def jira_is_configured(self) -> bool:
        return bool(
            self.jira_base_url
            and self.jira_email
            and self.jira_api_token
        )

    @property
    def freshservice_is_configured(self) -> bool:
        return bool(self.freshservice_domain and self.freshservice_api_key)

    @property
    def assistant_is_configured(self) -> bool:
        return bool(self.assistant_enabled and self.openrouter_api_key)

    @property
    def agile_is_configured(self) -> bool:
        return bool(self.jira_is_configured and self.jira_board_id is not None)


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
