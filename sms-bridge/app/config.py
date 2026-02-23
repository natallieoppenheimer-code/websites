from pydantic import BaseSettings


class Settings(BaseSettings):
    provider: str = "textlink_sms"
    textlink_sms_api_key: str = ""
    textlink_sms_api_url: str = "https://textlinksms.com/api/send-sms"
    brave_api_key: str = ""
    brave_api_url: str = "https://api.search.brave.com/res/v1/web/search"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        fields = {
            "textlink_sms_api_key": {"env": "TEXTLINK_SMS_API_KEY"},
            "textlink_sms_api_url": {"env": "TEXTLINK_SMS_API_URL"},
            "brave_api_key": {"env": "BRAVE_API_KEY"},
            "brave_api_url": {"env": "BRAVE_API_URL"},
        }


settings = Settings()
