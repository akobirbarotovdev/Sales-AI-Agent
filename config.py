import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "sales_agent"
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite:///./sales_agent.db"
    max_retries: int = 3
    sonnet_timeout: int = 120
    haiku_timeout: int = 60

    @property
    def sonnet_model(self) -> str:
        return "claude-sonnet-4-6"

    @property
    def haiku_model(self) -> str:
        return "claude-haiku-4-5-20251001"

    @property
    def simulation_mode(self) -> bool:
        key = self.anthropic_api_key or ""
        return not key or key.startswith("sk-ant-...") or "..." in key or len(key) < 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
