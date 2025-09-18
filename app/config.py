from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./lms.db" 
    DEFAULT_LEAVE_BALANCE: int = 20

settings = Settings()