import pytest

from doclify.components.config import load_config, update_config
from doclify.components.init import init_project


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text("def greeting():\n    return 'hello'\n", encoding="utf-8")


def test_init_preserves_ignore_content_and_model(tmp_path):
    original = "# keep this comment\n\nignored.py\n"
    (tmp_path / ".gitignore").write_text(original, encoding="utf-8")
    init_project()
    update_config("llama-3.3-70b-versatile")
    init_project()
    assert load_config().llm.model == "llama-3.3-70b-versatile"
    content = (tmp_path / ".gitignore").read_text()
    assert content.startswith(original)
    assert content.count(".doclify/") == 1


@pytest.mark.parametrize(
    "document",
    [
        "[]",
        "project: demo\nproject: other\nstructure: [main.py]",
        "project: demo\nstructure: [main.py, main.py]",
        "project: demo\nstructure: [../outside.py]",
        "project: demo\nstructure: [main.py]\nllm:\n  timeout: 0",
        "project: demo\nstructure: [main.py]\nllm:\n  api_key: do-not-store-keys",
    ],
)
def test_invalid_config_is_rejected_without_overwrite(tmp_path, document):
    (tmp_path / "doclify.yaml").write_text(document, encoding="utf-8")
    with pytest.raises(ValueError):
        load_config()
    with pytest.raises(ValueError):
        init_project()
    assert (tmp_path / "doclify.yaml").read_text() == document
