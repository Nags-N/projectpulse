"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROJECTPULSE_")

    app_name: str = "ProjectPulse AI"
    database_url: str = "sqlite:///./data/projectpulse.db"
    api_prefix: str = "/api"

    @property
    def data_dir(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite:///"):
            db_path = Path(url.replace("sqlite:///", ""))
            return db_path.parent
        return Path("data")


settings = Settings()
