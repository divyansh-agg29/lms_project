from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./lms.db" 
    DEFAULT_LEAVE_BALANCE: int = 20

    SECRET_KEY: str = "secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

settings = Settings()