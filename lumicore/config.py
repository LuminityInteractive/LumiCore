import os

class Settings:
    app_env: str
    debug: bool
    host: str
    port: int
    log_level: str
    database_url: str
    jwt_secret: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "development")
        self.debug = os.getenv("APP_DEBUG", "false").lower() == "true"
        self.host = os.getenv("APP_HOST", "127.0.0.1")
        self.port = int(os.getenv("APP_PORT", "8000"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.database_url = os.getenv("DATABASE_URL", "")
        self.jwt_secret = os.getenv("JWT_SECRET", "")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

settings = Settings()
