import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Settings:
    # Server Configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL_GPT: str = os.getenv("MODEL_NAME", os.getenv("OPENAI_MODEL_GPT", "gpt-3.5-turbo"))
    OPENAI_MODEL_WHISPER: str = os.getenv("OPENAI_MODEL_WHISPER", "whisper-1")
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    
    # Interview Configuration
    MAX_QUESTIONS: int = int(os.getenv("MAX_QUESTIONS", "3"))
    FOLLOWUP_TIMEOUT: int = int(os.getenv("FOLLOWUP_TIMEOUT", "30"))
    
    # Audio Configuration
    MAX_AUDIO_SIZE: int = int(os.getenv("MAX_AUDIO_SIZE", "25000000"))  # 25MB
    SUPPORTED_AUDIO_FORMATS: List[str] = ["wav", "mp3", "m4a", "webm"]
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        
        if cls.MAX_QUESTIONS <= 0:
            raise ValueError("MAX_QUESTIONS must be positive")

settings = Settings()

# Validate settings on import
if __name__ != "__main__":
    try:
        settings.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        if settings.DEBUG:
            print("Running in development mode with default/missing values")