from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AgentTalk Admin Backend"
    app_env: str = "production"
    jwt_secret: str = "admin-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5174,http://localhost:8061"

    db_dsn: str = "postgresql://user:CHANGE_ME_POSTGRES_PASSWORD@db:5432/agenttalk"
    redis_url: str = "redis://:CHANGE_ME_REDIS_PASSWORD@redis:6379/0"

    backend_base_url: str = "http://backend:8080"
    agent_service_base_url: str = "http://agent_service:8001"
    agent_service_runtime_token: str = "CHANGE_ME_RUNTIME_CONFIG_TOKEN"
    agent_model_secret: str = ""

    admin_init_username: str = "superadmin"
    admin_init_password: str = "CHANGE_ME_ADMIN_PASSWORD"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
