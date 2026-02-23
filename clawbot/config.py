"""Configuration management for Clawbot"""
import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    from pydantic import ConfigDict as _ConfigDict
    _HAS_SETTINGS = True
except ImportError:
    BaseSettings = None  # type: ignore
    _HAS_SETTINGS = False


if _HAS_SETTINGS:
    class Settings(BaseSettings):
        """Application settings (pydantic-settings v2)"""
        model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}

        TEXTLINK_API_KEY: Optional[str] = None
        TEXTLINK_WEBHOOK_SECRET: Optional[str] = None
        ELEVENLABS_API_KEY: Optional[str] = None
        CLAWBOT_BASE_URL: str = "http://localhost:8000"
        OPENCLAW_GATEWAY_URL: str = "http://127.0.0.1:18789"
        OPENCLAW_HOOKS_TOKEN: str = "clawbot-hook-secret"
        GOOGLE_CLIENT_ID: Optional[str] = None
        GOOGLE_CLIENT_SECRET: Optional[str] = None
        GOOGLE_REDIRECT_URI: Optional[str] = None
        GOOGLE_SCOPES: str = (
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.send "
            "https://www.googleapis.com/auth/calendar "
            "https://www.googleapis.com/auth/calendar.events "
            "https://www.googleapis.com/auth/admin.directory.user.readonly "
            "https://www.googleapis.com/auth/admin.directory.group.readonly "
            "https://www.googleapis.com/auth/spreadsheets"
        )
        TOKEN_CACHE_TYPE: str = "file"
        TOKEN_CACHE_PATH: str = "./.token_cache"
        REDIS_HOST: Optional[str] = None
        REDIS_PORT: int = 6379
        REDIS_DB: int = 0
        REDIS_PASSWORD: Optional[str] = None
        ENABLE_MULTI_AGENT: bool = True
        AGENT_ROUTING_STRATEGY: str = "round_robin"
        API_HOST: str = "0.0.0.0"
        API_PORT: int = 8000
else:
    # Fallback to environment variables
    class Settings:
        """Application settings using environment variables"""
        
        def __init__(self):
            from dotenv import load_dotenv
            load_dotenv()
        
        @property
        def TEXTLINK_API_KEY(self) -> Optional[str]:
            return os.getenv("TEXTLINK_API_KEY")

        @property
        def TEXTLINK_WEBHOOK_SECRET(self) -> Optional[str]:
            return os.getenv("TEXTLINK_WEBHOOK_SECRET")

        @property
        def OPENCLAW_GATEWAY_URL(self) -> str:
            return os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")

        @property
        def OPENCLAW_HOOKS_TOKEN(self) -> str:
            return os.getenv("OPENCLAW_HOOKS_TOKEN", "clawbot-hook-secret")

        @property
        def ELEVENLABS_API_KEY(self) -> Optional[str]:
            return os.getenv("ELEVENLABS_API_KEY")

        @property
        def CLAWBOT_BASE_URL(self) -> str:
            return os.getenv("CLAWBOT_BASE_URL", "http://localhost:8000")

        @property
        def GOOGLE_CLIENT_ID(self) -> Optional[str]:
            return os.getenv("GOOGLE_CLIENT_ID")
        
        @property
        def GOOGLE_CLIENT_SECRET(self) -> Optional[str]:
            return os.getenv("GOOGLE_CLIENT_SECRET")
        
        @property
        def GOOGLE_REDIRECT_URI(self) -> Optional[str]:
            return os.getenv("GOOGLE_REDIRECT_URI")
        
        @property
        def GOOGLE_SCOPES(self) -> str:
            return os.getenv(
                "GOOGLE_SCOPES",
                "https://www.googleapis.com/auth/gmail.readonly "
                "https://www.googleapis.com/auth/gmail.send "
                "https://www.googleapis.com/auth/calendar "
                "https://www.googleapis.com/auth/calendar.events "
                "https://www.googleapis.com/auth/admin.directory.user.readonly "
                "https://www.googleapis.com/auth/admin.directory.group.readonly "
                "https://www.googleapis.com/auth/spreadsheets"
            )
        
        @property
        def TOKEN_CACHE_TYPE(self) -> str:
            return os.getenv("TOKEN_CACHE_TYPE", "file")
        
        @property
        def TOKEN_CACHE_PATH(self) -> str:
            return os.getenv("TOKEN_CACHE_PATH", "./.token_cache")
        
        @property
        def REDIS_HOST(self) -> Optional[str]:
            return os.getenv("REDIS_HOST")
        
        @property
        def REDIS_PORT(self) -> int:
            return int(os.getenv("REDIS_PORT", "6379"))
        
        @property
        def REDIS_DB(self) -> int:
            return int(os.getenv("REDIS_DB", "0"))
        
        @property
        def REDIS_PASSWORD(self) -> Optional[str]:
            return os.getenv("REDIS_PASSWORD")
        
        @property
        def ENABLE_MULTI_AGENT(self) -> bool:
            return os.getenv("ENABLE_MULTI_AGENT", "true").lower() == "true"
        
        @property
        def AGENT_ROUTING_STRATEGY(self) -> str:
            return os.getenv("AGENT_ROUTING_STRATEGY", "round_robin")
        
        @property
        def API_HOST(self) -> str:
            return os.getenv("API_HOST", "0.0.0.0")
        
        @property
        def API_PORT(self) -> int:
            return int(os.getenv("API_PORT", "8000"))


# Instantiate settings
if BaseSettings:
    # Pydantic BaseSettings - instantiate directly
    settings = Settings()
else:
    # Fallback Settings class - needs instantiation
    settings = Settings()
