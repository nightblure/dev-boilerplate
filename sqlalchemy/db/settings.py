from pydantic_settings import BaseSettings, SettingsConfigDict


# Pydantic V2
class DbSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='DB_',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    db_url: str = 'sqlite:///db.db'
    is_need_log_sql: bool = True
    
