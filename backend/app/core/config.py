from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://admin:Gokul123@localhost:5432/consumer_sim"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()