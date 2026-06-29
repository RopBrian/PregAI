"""Application configuration using Pydantic Settings"""
import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Global application settings"""
    app_name: str = 'PregnancyAI'
    app_version: str = '1.0.0'
    debug: bool = False
    log_level: str = 'INFO'

    openrouter_api_key: str = Field(validation_alias='OPENROUTER_API_KEY')
    openrouter_model: str = Field(default='tngtech/deepseek-r1t2-chimera:free', validation_alias='OPENROUTER_MODEL')
    openrouter_base_url: str = Field(default='https://openrouter.ai/api/v1', validation_alias='OPENROUTER_BASE_URL')
    openrouter_daily_limit: int = Field(default=50, validation_alias='OPENROUTER_DAILY_LIMIT')
    openrouter_minute_limit: int = Field(default=20, validation_alias='OPENROUTER_MINUTE_LIMIT')

    gemini_api_key: Optional[str] = Field(default=None, validation_alias='GEMINI_API_KEY')

    database_url: str = Field(validation_alias='DATABASE_URL')
    enable_ml_analysis: bool = Field(default=False, validation_alias='ENABLE_ML_ANALYSIS')
    ml_model_version: str = Field(default='v1', validation_alias='ML_MODEL_VERSION')

    secret_key: str = Field(validation_alias='SECRET_KEY')
    algorithm: str = Field(default='HS256', validation_alias='ALGORITHM')
    access_token_expire_minutes: int = Field(default=30, validation_alias='ACCESS_TOKEN_EXPIRE_MINUTES')

    auto_create_tables: bool = Field(default=False, validation_alias='AUTO_CREATE_TABLES')
    pregai_admin_username: str = Field(default='admin', validation_alias='PREGAI_ADMIN_USERNAME')
    pregai_admin_email: str = Field(default='admin@pregai.com', validation_alias='PREGAI_ADMIN_EMAIL')
    pregai_admin_password: Optional[str] = Field(default=None, validation_alias='PREGAI_ADMIN_PASSWORD')

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
        populate_by_name=True
    )


settings = Settings()  # type: ignore[call-arg]
