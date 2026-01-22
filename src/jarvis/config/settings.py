"""Configuration management for JARVIS using Pydantic Settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GarminSettings(BaseSettings):
    """Garmin Connect credentials."""

    model_config = SettingsConfigDict(env_prefix="GARMIN_", env_file=".env", extra="ignore")

    email: str = ""
    password: SecretStr = SecretStr("")


class WhoopSettings(BaseSettings):
    """Whoop API OAuth settings."""

    model_config = SettingsConfigDict(env_prefix="WHOOP_", env_file=".env", extra="ignore")

    client_id: str = ""
    client_secret: SecretStr = SecretStr("")
    redirect_uri: str = "http://localhost:8080/callback"
    access_token: SecretStr = SecretStr("")
    refresh_token: SecretStr = SecretStr("")


class GoogleSettings(BaseSettings):
    """Google Calendar OAuth settings."""

    model_config = SettingsConfigDict(env_prefix="GOOGLE_", env_file=".env", extra="ignore")

    credentials_file: Path = Path("~/.config/jarvis/google_credentials.json")
    token_file: Path = Path("~/.config/jarvis/google_token.json")


class MicrosoftSettings(BaseSettings):
    """Microsoft Graph (Outlook) OAuth settings."""

    model_config = SettingsConfigDict(env_prefix="MICROSOFT_", env_file=".env", extra="ignore")

    client_id: str = ""
    client_secret: SecretStr = SecretStr("")
    tenant_id: str = "common"


class ObsidianSettings(BaseSettings):
    """Obsidian vault settings."""

    model_config = SettingsConfigDict(env_prefix="OBSIDIAN_", env_file=".env", extra="ignore")

    vault_path: Path = Path("~/Documents/Obsidian")
    daily_notes_folder: str = "Daily Notes"
    daily_note_format: str = "%Y-%m-%d"


class HomeAssistantSettings(BaseSettings):
    """Home Assistant settings."""

    model_config = SettingsConfigDict(env_prefix="HOME_ASSISTANT_", env_file=".env", extra="ignore")

    url: str = "http://homeassistant.local:8123"
    token: SecretStr = SecretStr("")


class VoiceSettings(BaseSettings):
    """Voice assistant settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    picovoice_access_key: SecretStr = Field(default=SecretStr(""), alias="PICOVOICE_ACCESS_KEY")
    wake_word: str = Field(default="jarvis", alias="WAKE_WORD")
    whisper_model: str = Field(default="base", alias="WHISPER_MODEL")


class OpenRouterSettings(BaseSettings):
    """OpenRouter API settings for Clawd."""

    model_config = SettingsConfigDict(env_prefix="OPENROUTER_", env_file=".env", extra="ignore")

    api_key: SecretStr = SecretStr("")
    model: str = "openai/gpt-5.2"  # GPT-5.2


class DatabaseSettings(BaseSettings):
    """Database settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    database_url: str = Field(
        default="sqlite:///~/.local/share/jarvis/jarvis.db", alias="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")


class PiSettings(BaseSettings):
    """Raspberry Pi deployment settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    pi5_host: str = Field(default="pi5.local", alias="PI5_HOST")
    pi5_user: str = Field(default="pi", alias="PI5_USER")
    pi4_host: str = Field(default="pi4.local", alias="PI4_HOST")
    pi4_user: str = Field(default="pi", alias="PI4_USER")


class Settings(BaseSettings):
    """Main JARVIS settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    environment: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    timezone: str = "America/Los_Angeles"

    # API Keys
    anthropic_api_key: SecretStr = Field(default=SecretStr(""), alias="ANTHROPIC_API_KEY")

    # Sub-settings
    garmin: GarminSettings = Field(default_factory=GarminSettings)
    whoop: WhoopSettings = Field(default_factory=WhoopSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    microsoft: MicrosoftSettings = Field(default_factory=MicrosoftSettings)
    obsidian: ObsidianSettings = Field(default_factory=ObsidianSettings)
    home_assistant: HomeAssistantSettings = Field(default_factory=HomeAssistantSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    pi: PiSettings = Field(default_factory=PiSettings)
    openrouter: OpenRouterSettings = Field(default_factory=OpenRouterSettings)


# Global settings instance
settings = Settings()
