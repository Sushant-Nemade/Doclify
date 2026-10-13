import json
import re

from doclify.utils.scanner import validate_source

MAX_FILE_SIZE = 256_000
CHUNK_SIZE_LIMIT = 24_000
SECRET_PATTERN = re.compile(
    r"(?:ghp_|github_pat_|gsk_|sk-proj-)[A-Za-z0-9_-]{12,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\n]{12,}['\"]",
    re.IGNORECASE,
)


def read_source(file_path: str) -> tuple[str, bytes]:
    path = validate_source(file_path)
    with path.open("rb") as handle:
        raw = handle.read(MAX_FILE_SIZE + 1)
    if len(raw) > MAX_FILE_SIZE:
        raise ValueError("Source file exceeds 256 KB")
    try:
        content = raw.decode("utf-8")
    except UnicodeError as error:
        raise ValueError("Source must be UTF-8 text") from error
    if "\x00" in content:
        raise ValueError("Binary source rejected")
    if path.suffix.lower() == ".ipynb":
        try:
            document = json.loads(content)
            cells = document["cells"]
            if not isinstance(cells, list):
                raise ValueError
            snippets = []
            for cell in cells:
                if cell.get("cell_type") in {"code", "markdown"}:
                    source = cell.get("source", [])
                    if isinstance(source, list) and all(isinstance(line, str) for line in source):
                        source = "".join(source)
                    if not isinstance(source, str):
                        raise ValueError
                    snippets.append(source)
            content = "\n\n".join(snippets)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise ValueError("Invalid notebook structure") from error
    if SECRET_PATTERN.search(content):
        raise ValueError(
            "Potential credential found in source; exclude or sanitize it before processing"
        )
    return content, raw


def extract_file_content(file_path: str) -> list[str]:
    content, _ = read_source(file_path)
    return [
        content[index : index + CHUNK_SIZE_LIMIT]
        for index in range(0, max(len(content), 1), CHUNK_SIZE_LIMIT)
    ]
