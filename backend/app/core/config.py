from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg2://gachiga:gachiga@db:5432/gachiga"
    REDIS_URL: str = "redis://redis:6379/0"

    JWT_SECRET_KEY: str = "changeme"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14

    # 개인정보(전화번호) 암호화 키 — 비우면 JWT_SECRET_KEY에서 파생
    PHONE_ENC_KEY: str = ""

    SENTRY_DSN: str = ""

    # 매칭 엔진
    MATCHING_LOOP_ENABLED: bool = True
    MATCH_INTERVAL_SECONDS: int = 30
    MATCH_ORIGIN_EPS_KM: float = 0.8
    MATCH_DEST_EPS_KM: float = 0.8
    MATCH_MAX_GROUP: int = 3
    MATCH_MAX_DETOUR: float = 1.3
    MATCH_MIN_OVERLAP_MIN: float = 5.0


settings = Settings()
