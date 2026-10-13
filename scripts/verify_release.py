import json
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify():
    wheels = sorted((ROOT / "dist").glob("doclify_portfolio-*.whl"))
    archives = sorted((ROOT / "dist").glob("doclify_portfolio-*.tar.gz"))
    if len(wheels) != 1 or len(archives) != 1:
        raise ValueError("Expected exactly one derivative wheel and one source archive")
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = wheel.namelist()
        for required in [
            "doclify/prompts/batch_summary.txt",
            "doclify/prompts/final_summary.txt",
            "doclify/resources/Python.gitignore",
            "doclify/__main__.py",
        ]:
            if required not in names:
                raise ValueError("Wheel is missing a runtime resource")
        for legal in ["LICENSE", "NOTICE.md"]:
            if not any(name.endswith("/licenses/" + legal) for name in names):
                raise ValueError("Wheel is missing a license or attribution notice")
    with tarfile.open(archives[0]) as archive:
        names = archive.getnames()
        for required in [
            "scripts/verify_release.py",
            "tests/test_pipeline.py",
            "examples/tiny_project/main.py",
            "docs/OPERATIONS.md",
            "NOTICE.md",
        ]:
            if not any(name.endswith("/" + required) for name in names):
                raise ValueError("Source archive lacks build/test material")
        if any("/.env" in name or "/.doclify/" in name or "/.venv/" in name for name in names):
            raise ValueError("Private state found in source archive")
    with tempfile.TemporaryDirectory(prefix="doclify-wheel-") as directory:
        root = Path(directory)
        site = root / "site"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--target",
                str(site),
                str(wheels[0]),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        project = root / "project"
        project.mkdir()
        (project / "main.py").write_text("def greeting():\n    return 'hello'\n", encoding="utf-8")
        code = f"import sys; sys.path.insert(0, {str(site)!r}); from pathlib import Path; import doclify; assert Path(doclify.__file__).is_relative_to(Path({str(site)!r})); from doclify.utils.utils import get_prompt; assert get_prompt('batch_summary'); from click.testing import CliRunner; from doclify.pipelines.supervisor import cli; import json; runner=CliRunner(); initialized=runner.invoke(cli,['init']); assert initialized.exit_code == 0, initialized.output; generated=runner.invoke(cli,['run','--offline']); assert generated.exit_code == 0, generated.output; digest=json.loads(generated.output)['digest']; published=runner.invoke(cli,['publish','--approve',digest]); assert published.exit_code == 0, published.output; assert Path('README.generated.md').is_file(); print(json.dumps({{'wheel_cli':'passed','version':doclify.__version__}}))"
        subprocess.run([sys.executable, "-I", "-c", code], cwd=project, check=True)
    print(
        json.dumps(
            {"wheel_resources": "passed", "source_material": "passed", "license": "AGPL-3.0-only"}
        )
    )


if __name__ == "__main__":
    verify()
