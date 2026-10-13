import socket
from pathlib import Path

from click.testing import CliRunner


def test_help_has_no_project_or_network_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    def forbidden_connection(*args, **kwargs):
        raise AssertionError("Help must not contact a provider")

    monkeypatch.setattr(socket, "create_connection", forbidden_connection)
    from doclify.pipelines.supervisor import cli

    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output
    assert "run" in result.output
    assert list(Path.cwd().iterdir()) == []


def test_models_without_key_returns_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from doclify.pipelines.supervisor import cli

    result = CliRunner().invoke(cli, ["models"])
    assert result.exit_code != 0
    assert "GROQ_API_KEY is missing" in result.output


def test_legal_notice_includes_source_and_license():
    from doclify.pipelines.supervisor import cli

    result = CliRunner().invoke(cli, ["--license"])
    assert result.exit_code == 0
    assert "AGPL" in result.output and "Hema Kalyan" in result.output
    assert "https://github.com/Sushant-Nemade/doclify" in result.output
