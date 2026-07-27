from pydantic import AnyHttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: PostgresDsn

    jira_base_url: AnyHttpUrl | None = None
    jira_email: str | None = None
    jira_api_token: SecretStr | None = None

    jira_project_identity: str | None = None
    jira_project_finance: str | None = None
    jira_project_platform: str | None = None

    llm_enabled: bool = False
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:8b"
    llm_confidence_threshold: float = 0.7
    llm_timeout_seconds: int = 20

    @property
    def jira_is_configured(self) -> bool:
        return bool(
            self.jira_base_url
            and self.jira_email
            and self.jira_api_token
        )


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
