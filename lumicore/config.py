import os

class Settings:
    app_env: str
    debug: bool
    host: str
    port: int
    log_level: str
    database_url: str

    def __init__(self) -> None:
        self.app_env = os.getenv("APP_ENV", "development")
        self.debug = os.getenv("APP_DEBUG", "false").lower() == "true"
        self.host = os.getenv("APP_HOST", "127.0.0.1")
        self.port = int(os.getenv("APP_PORT", "8000"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.database_url = os.getenv("DATABASE_URL", "")

settings = Settings()
