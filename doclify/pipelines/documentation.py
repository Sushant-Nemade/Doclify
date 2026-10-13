import hashlib
import hmac
import json
import re

from pydantic import ValidationError

from doclify.components.config import load_config
from doclify.schema.schema import LLMConfig
from doclify.utils.extract import CHUNK_SIZE_LIMIT, read_source
from doclify.utils.file_utils import (
    atomic_write,
    clean_cache,
    load_cache,
    pipeline_lock,
    project_path,
    save_cache,
)
from doclify.utils.llm import generate_doc
from doclify.utils.utils import get_prompt

MAX_PROJECT_BYTES = 2_000_000
MAX_CONTEXT_CHARS = 64_000
MAX_DRAFT_BYTES = 256_000


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _context(config: LLMConfig) -> str:
    content = (
        json.dumps(config.model_dump(), sort_keys=True)
        + get_prompt("batch_summary")
        + get_prompt("final_summary")
        + "extract-v2"
    )
    return _digest(content.encode("utf-8"))


def _collect(config) -> dict:
    sources = {}
    total_bytes = 0
    for name in config.structure:
        content, raw = read_source(name)
        total_bytes += len(raw)
        if total_bytes > MAX_PROJECT_BYTES:
            raise ValueError("Selected project exceeds 2 MB")
        sources[name] = {"content": content, "hash": _digest(raw)}
    return sources


def _selection(files: list[str], target: str) -> set[str]:
    if target == ".":
        return set(files)
    canonical = target.replace("\\", "/").rstrip("/")
    project_path(canonical)
    selected = {name for name in files if name == canonical or name.startswith(canonical + "/")}
    if not selected:
        raise ValueError("Update target is not in the manifest; review doclify.yaml or rerun init")
    return selected


def _generate(
    config, sources: dict, cache: dict, context: str, stale: set[str], report: dict
) -> dict:
    for name, source in sources.items():
        if name not in stale:
            continue
        content = source["content"]
        chunks = [
            content[index : index + CHUNK_SIZE_LIMIT]
            for index in range(0, max(len(content), 1), CHUNK_SIZE_LIMIT)
        ]
        summaries = [
            generate_doc(
                chunk,
                "batch_summary",
                config.llm,
                metadata={"path": name, "project_name": config.project},
            )
            for chunk in chunks
        ]
        summary = "\n\n".join(summaries).strip()
        if not summary or len(summary) > 8000:
            raise ValueError("File summary is empty or exceeds the bounded cache limit")
        cache["files"][name] = {"hash": source["hash"], "context": context, "summary": summary}
        save_cache(cache)
    save_cache(cache)
    aggregated = "\n\n".join(
        f"### `{name}`\n\n{cache['files'][name]['summary']}" for name in config.structure
    )
    if len(aggregated) > MAX_CONTEXT_CHARS:
        raise ValueError("Final summary context exceeds 64,000 characters; reduce the manifest")
    output = generate_doc(
        aggregated, "final_summary", config.llm, metadata={"project_name": config.project}
    ).strip()
    wrapper = re.fullmatch(r"```(?:markdown|md)?\s*\n(.*)\n```\s*", output, flags=re.DOTALL)
    if wrapper:
        output = wrapper.group(1).strip()
    if not output or not output.startswith("# ") or len(output.encode("utf-8")) > MAX_DRAFT_BYTES:
        raise ValueError("Generated README is empty, oversized or missing its title")
    output += "\n"
    digest = _digest(output.encode("utf-8"))
    artifact = f".doclify/generated_artifacts/README-{digest}.md"
    atomic_write(artifact, output)
    manifest = {
        "digest": digest,
        "artifact": artifact,
        "provider": config.llm.provider,
        "sources": {name: source["hash"] for name, source in sources.items()},
    }
    atomic_write(".doclify/draft.json", json.dumps(manifest, indent=2) + "\n")
    return {**report, "draft": artifact, "digest": digest, "published": False}


def run_docs(model=None, provider=None, *, dry_run=False, allow_upload=False, target=".") -> dict:
    config = load_config()
    settings = config.llm.model_dump()
    if model is not None:
        settings["model"] = model
    if provider is not None:
        settings["provider"] = provider
    try:
        config.llm = LLMConfig.model_validate(settings)
    except ValidationError as error:
        raise ValueError("Invalid provider or model override") from error
    sources = _collect(config)
    selected = _selection(config.structure, target)
    context = _context(config.llm)

    def prepare():
        cache = clean_cache(load_cache(), config.structure)
        stale = {
            name
            for name, source in sources.items()
            if cache["files"].get(name, {}).get("hash") != source["hash"]
            or cache["files"].get(name, {}).get("context") != context
        }
        if not stale.issubset(selected):
            raise ValueError(
                "Other manifest files have stale summaries; run doclify run or update ."
            )
        requests = 1 + sum(
            max(1, (len(sources[name]["content"]) + CHUNK_SIZE_LIMIT - 1) // CHUNK_SIZE_LIMIT)
            for name in stale
        )
        if requests > config.llm.max_requests:
            raise ValueError("Run exceeds the configured request budget; reduce selected files")
        report = {
            "provider": config.llm.provider,
            "files": len(sources),
            "reused": len(sources) - len(stale),
            "planned_logical_requests": requests,
            "max_http_attempts": 0
            if config.llm.provider == "offline"
            else requests * (config.llm.max_retries + 1),
            "dry_run": dry_run,
        }
        return cache, stale, report

    if dry_run:
        return prepare()[2]
    if config.llm.provider == "groq" and not allow_upload:
        raise ValueError(
            "Groq receives selected source code; review a dry-run and pass --allow-upload, or use --offline"
        )
    with pipeline_lock():
        cache, stale, report = prepare()
        return _generate(config, sources, cache, context, stale, report)


def publish_readme(approval: str, *, replace_readme: bool = False) -> dict:
    if not re.fullmatch(r"[a-f0-9]{64}", approval):
        raise ValueError("Approval must be the full SHA-256 digest of the reviewed draft")
    with pipeline_lock():
        manifest_path = project_path(".doclify/draft.json", must_exist=True)
        if manifest_path.stat().st_size > 64_000:
            raise ValueError("Draft manifest exceeds its size limit")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as error:
            raise ValueError("Invalid draft manifest") from error
        if (
            not isinstance(manifest, dict)
            or not isinstance(manifest.get("digest"), str)
            or not hmac.compare_digest(approval, manifest["digest"])
        ):
            raise ValueError("Approval does not match the current draft")
        expected = f".doclify/generated_artifacts/README-{approval}.md"
        if manifest.get("artifact") != expected:
            raise ValueError("Invalid draft artifact path")
        path = project_path(expected, must_exist=True)
        with path.open("rb") as handle:
            content = handle.read(MAX_DRAFT_BYTES + 1)
        if len(content) > MAX_DRAFT_BYTES or _digest(content) != approval:
            raise ValueError("Draft changed after review; regenerate and inspect it")
        sources = _collect(load_config())
        if manifest.get("sources") != {name: source["hash"] for name, source in sources.items()}:
            raise ValueError(
                "Source files changed since generation; refresh and review a new draft"
            )
        destination = "README.md" if replace_readme else "README.generated.md"
        output = project_path(destination)
        backup = None
        if replace_readme and output.exists():
            if output.stat().st_size > MAX_DRAFT_BYTES:
                raise ValueError("Existing README exceeds the backup limit")
            previous = output.read_bytes()
            if previous != content:
                backup = f".doclify/backups/README-{_digest(previous)}.md"
                atomic_write(backup, previous.decode("utf-8"))
        atomic_write(destination, content.decode("utf-8"))
        return {"published": destination, "digest": approval, "backup": backup}
