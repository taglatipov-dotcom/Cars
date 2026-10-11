from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    CALCUS_API_KEY: str
    API_CLIENT_ID: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()