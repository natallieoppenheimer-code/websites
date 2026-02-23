"""Configuration management for Clawbot"""
import os
from typing import Optional

# Try to import BaseSettings from pydantic_settings (v2) or pydantic (v1)
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        # Fallback to environment variables if pydantic not available
        BaseSettings = None


if BaseSettings:
    class Settings(BaseSettings):
        """Application settings"""
        
        # TextLink / SMS
        TEXTLINK_API_KEY: Optional[str] = None
        TEXTLINK_WEBHOOK_SECRET: Optional[str] = None

        # ElevenLabs (voice notes for SMS realism)
        ELEVENLABS_API_KEY: Optional[str] = None
        CLAWBOT_BASE_URL: str = "http://localhost:8000"

        # OpenClaw gateway (for forwarding incoming SMS to the agent)
        OPENCLAW_GATEWAY_URL: str = "http://127.0.0.1:18789"
        OPENCLAW_HOOKS_TOKEN: str = "clawbot-hook-secret"
        
        # Google OAuth2 Configuration
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
        
        # Token Cache Configuration
        TOKEN_CACHE_TYPE: str = "file"  # "file" or "redis"
        TOKEN_CACHE_PATH: str = "./.token_cache"
        REDIS_HOST: Optional[str] = None
        REDIS_PORT: int = 6379
        REDIS_DB: int = 0
        REDIS_PASSWORD: Optional[str] = None
        
        # Multi-Agent Configuration
        ENABLE_MULTI_AGENT: bool = True
        AGENT_ROUTING_STRATEGY: str = "round_robin"  # "round_robin", "load_balance", "intent_based"
        
        # API Configuration
        API_HOST: str = "0.0.0.0"
        API_PORT: int = 8000
        
        class Config:
            env_file = ".env"
            case_sensitive = True
            extra = "ignore"
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
