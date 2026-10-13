from pathlib import Path

from doclify.components.config import load_config, write_config
from doclify.schema.schema import ProjectConfig
from doclify.utils.file_utils import atomic_write, pipeline_lock, project_path
from doclify.utils.scanner import scan_repo


def init_project() -> ProjectConfig:
    with pipeline_lock():
        existing = load_config() if project_path("doclify.yaml").exists() else None
        discovered = scan_repo()["structure"]
        if not discovered:
            raise ValueError("No supported source files found")
        config = ProjectConfig(
            project=existing.project if existing else Path.cwd().name,
            structure=discovered,
            llm=existing.llm if existing else {},
        )
        ignore_path = project_path(".gitignore")
        original = ignore_path.read_text(encoding="utf-8") if ignore_path.exists() else ""
        additions = [
            entry
            for entry in (".doclify/", "doclify.yaml", "README.generated.md")
            if entry not in original.splitlines()
        ]
        if additions:
            suffix = "" if not original or original.endswith("\n") else "\n"
            atomic_write(".gitignore", original + suffix + "\n".join(additions) + "\n")
        write_config(config)
        return config
