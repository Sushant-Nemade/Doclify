import hashlib
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from doclify.components.init import init_project
from doclify.pipelines.documentation import publish_readme, run_docs
from doclify.pipelines.supervisor import cli


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    (tmp_path / "main.py").write_text("def greeting():\n    return 'hello'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Existing human documentation\n", encoding="utf-8")
    init_project()


def test_offline_draft_then_reviewed_publication(tmp_path):
    result = run_docs(provider="offline")
    assert result["published"] is False
    assert (tmp_path / "README.md").read_text().startswith("# Existing")
    draft = (tmp_path / result["draft"]).read_text()
    assert "No AI inference" in draft and "greeting" in draft
    assert hashlib.sha256((tmp_path / result["draft"]).read_bytes()).hexdigest() == result["digest"]
    published = publish_readme(result["digest"])
    assert published["published"] == "README.generated.md"
    assert (tmp_path / "README.md").read_text().startswith("# Existing")
    assert (tmp_path / "README.generated.md").read_text() == draft


def test_replace_readme_requires_explicit_option_and_backup(tmp_path):
    original = (tmp_path / "README.md").read_bytes()
    draft = run_docs(provider="offline")
    published = publish_readme(draft["digest"], replace_readme=True)
    assert (tmp_path / published["backup"]).read_bytes() == original
    assert (tmp_path / "README.md").read_bytes() == (tmp_path / draft["draft"]).read_bytes()


def test_modified_draft_rejects_old_approval(tmp_path):
    draft = run_docs(provider="offline")
    (tmp_path / draft["draft"]).write_text("# Tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        publish_readme(draft["digest"], replace_readme=True)
    assert (tmp_path / "README.md").read_text().startswith("# Existing")


def test_dry_run_has_no_network_or_disk_writes(tmp_path, monkeypatch):
    from doclify.pipelines import documentation

    def forbidden_generation(*args, **kwargs):
        pytest.fail("Dry-run invoked a generator")

    monkeypatch.setattr(documentation, "generate_doc", forbidden_generation)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    result = CliRunner().invoke(cli, ["run", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["dry_run"] is True
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after


def test_cache_reuses_unchanged_files_and_invalidates_changes(tmp_path):
    run_docs(provider="offline")
    assert run_docs(provider="offline")["reused"] == 1
    (tmp_path / "main.py").write_text("def changed():\n    return 'updated'\n", encoding="utf-8")
    updated = run_docs(provider="offline", target="main.py")
    assert updated["reused"] == 0
    assert "changed" in (tmp_path / updated["draft"]).read_text()


def test_remote_generation_requires_explicit_upload_permission():
    result = CliRunner().invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "--allow-upload" in result.output


def test_provider_failure_does_not_publish_or_erase_draft(tmp_path, monkeypatch):
    from doclify.pipelines import documentation

    prior = run_docs(provider="offline")

    def failed_generation(*args, **kwargs):
        raise ValueError("Simulated provider failure")

    monkeypatch.setattr(documentation, "generate_doc", failed_generation)
    with pytest.raises(ValueError):
        run_docs(provider="groq", allow_upload=True)
    manifest = json.loads((tmp_path / ".doclify/draft.json").read_text())
    assert manifest["digest"] == prior["digest"]
    assert (tmp_path / "README.md").read_text().startswith("# Existing")


def test_cli_missing_config_returns_failure(tmp_path):
    (tmp_path / "doclify.yaml").unlink()
    result = CliRunner().invoke(cli, ["run", "--offline"])
    assert result.exit_code != 0 and "init" in result.output


def test_invalid_approval_returns_nonzero():
    result = CliRunner().invoke(cli, ["publish", "--approve", "wrong"])
    assert result.exit_code != 0


def test_changed_source_rejects_previous_draft(tmp_path):
    draft = run_docs(provider="offline")
    (tmp_path / "main.py").write_text("print('changed')", encoding="utf-8")
    with pytest.raises(ValueError, match="Source files changed"):
        publish_readme(draft["digest"])
    assert not (tmp_path / "README.generated.md").exists()


def test_full_cli_offline_workflow():
    generated = CliRunner().invoke(cli, ["run", "--offline"])
    assert generated.exit_code == 0, generated.output
    digest = json.loads(generated.output)["digest"]
    published = CliRunner().invoke(cli, ["publish", "--approve", digest])
    assert published.exit_code == 0, published.output
    assert Path("README.generated.md").is_file()
