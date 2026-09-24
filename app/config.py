import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = os.getenv("APP_NAME")
    OTP_DURATION: int = int(os.getenv("OTP_DURATION"))
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES"))
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM")
    MAX_BCRYPT_BYTES: int = int(os.getenv("MAX_BCRYPT_BYTES"))
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALLOWED_ORIGINS: tuple[str, ...] = tuple(_split_csv(os.getenv("ALLOWED_ORIGINS")))
    BASE_URL: str = os.getenv("BASE_URL").rstrip("/")
    DATABASE_URL: str = os.getenv("DATABASE_URL") 
    PROFILE_URL: str = os.getenv("PROFILE_URL") 

    # Email
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL") 
    SENDER_PASSWORD: str = os.getenv("SENDER_PASSWORD") 
    

settings = Settings()
