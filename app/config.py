from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    allegro_client_id: str = ""
    allegro_client_secret: str = ""
    allegro_sandbox: bool = True
    allegro_redirect_uri: str = "http://localhost:8000/auth/callback"

    database_path: str = "./data/arbitrage.db"

    notify_telegram_bot_token: str = ""
    notify_telegram_chat_id: str = ""
    notify_smtp_host: str = ""
    notify_smtp_port: int = 587
    notify_smtp_user: str = ""
    notify_smtp_password: str = ""
    notify_smtp_from: str = ""
    notify_smtp_to: str = ""

    @property
    def api_base(self) -> str:
        return (
            "https://api.allegro.pl.allegrosandbox.pl"
            if self.allegro_sandbox
            else "https://api.allegro.pl"
        )

    @property
    def auth_base(self) -> str:
        return (
            "https://allegro.pl.allegrosandbox.pl/auth/oauth"
            if self.allegro_sandbox
            else "https://allegro.pl/auth/oauth"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
