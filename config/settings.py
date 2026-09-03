from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import Field,validator
from pathlib import Path
from typing import Optional,List
import os

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    groq_api_key: str = Field(..., description='Groq API key for LLM and STT')
    nvidia_api_key: Optional[str] = Field(None,description='NVIDIA NIM API key')

    llm_model: str = Field('llama-3.1-70b-versatile',description='LLM model to use')
    stt_model: str = Field("en-US-EmmaMultilingualNeural", description="TTS voice")

    chrome_path: str = Field(
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        description='Chrome executable path'
    )
    vscode_path: Optional[str] = Field(None,description='VS Code executable path')
    notepad_path: str = Field(
        r"C:\Windows\System32\notepad.exe",
        description='Notepad executable path'
    )

    require_confirmation_for_destructive: bool = Field(
        True,
        description='Require confirmation for destructive operations'
    )

    allowed_applications: List[str] = Field(
        ["chrome", "vscode", "notepad", "edge", "firefox"],
        description="List of allowed applications"
    )

    log_level: str = Field('INFO',description="Logging level")
    log_directory: str = Field('./logs',description="Log directory")

    memory_database: str = Field(
        "./memory/agent_memory.db",
        description="SQLite database path"
    )

    browser_headless: bool = Field(False, description="Run browser in headless mode")
    browser_timeout: int = Field(30000,description='Browser action timeout in ms')

    max_retries: int = Field(3,description='Maximum tool execution retries')
    tool_timeout: int = Field(30,description='Tool execution timeout in seconds')
    enable_vision: bool = Field(True,description="Enable screen vision capabilities")

    @validator('log_level')
    def validate_log_level(cls,v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    @property
    def log_dir(self) -> Path:
        path = Path(self.log_directory)
        path.parent.mkdir(parents=True,exist_ok=True)
        return path

    @property
    def memory_db_path(self) -> Path:
        path = Path(self.memory_database)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
settings = Settings()

def get_settings() -> Settings:
    return settings