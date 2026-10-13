from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from doclify.config.constants import LiteLLMConfig
from doclify.utils.file_utils import project_path


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    model: str = Field(
        default=LiteLLMConfig.DEFAULT_MODEL, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$"
    )
    provider: Literal["groq", "offline"] = "groq"
    timeout: int = Field(default=30, ge=1, le=120)
    max_retries: int = Field(default=1, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=64, le=4096)
    max_requests: int = Field(default=32, ge=1, le=64)


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    project: str = Field(min_length=1, max_length=100)
    structure: list[str] = Field(min_length=1, max_length=128)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @field_validator("project")
    @classmethod
    def valid_project(cls, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise ValueError("Project name contains control characters")
        return value

    @field_validator("structure")
    @classmethod
    def valid_structure(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("Manifest contains duplicate paths")
        for name in value:
            project_path(name)
        return value


class ReadmeResponse(BaseModel):
    final_readme: str = Field(min_length=1, max_length=64_000)
