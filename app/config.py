from urllib.parse import quote

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # RabbitMQ
    RABBITMQ_HOST: str = "91.98.64.92"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    RABBITMQ_VHOST: str = "default"
    RABBITMQ_QUEUE: str = "ajeboxe"

    # Redis
    REDIS_HOST: str = "91.98.64.92"
    REDIS_PORT: int = 6380
    REDIS_PASSWORD: str = ""

    # Google Gemini
    GEMINI_API_KEY: str = ""

    # UAZAPI
    UAZAPI_BASE_URL: str = "https://strategicai.uazapi.com"
    UAZAPI_TOKEN: str = ""
    UAZAPI_INSTANCE: str = "ajeboxe"

    # Google Sheets
    GOOGLE_CREDENTIALS_JSON: str = ""
    GOOGLE_SHEET_ID: str = ""

    # App
    WEBHOOK_PATH: str = "/ajeboxe"
    DEBOUNCE_SECONDS: int = 30
    BLOCK_TTL_SECONDS: int = 3600

    @property
    def rabbitmq_url(self) -> str:
        user = quote(self.RABBITMQ_USER, safe="")
        password = quote(self.RABBITMQ_PASS, safe="")
        vhost = quote(self.RABBITMQ_VHOST, safe="")
        return (
            f"amqp://{user}:{password}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{vhost}"
        )

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
