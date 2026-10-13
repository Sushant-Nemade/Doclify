# Doclify

An attributed documentation CLI with bounded source discovery, incremental
summaries, private drafts and explicit reviewed README publication.

**Status: tested local reference implementation.** Offline end-to-end workflows
and mocked Groq SDK requests are verified. Live Groq inference, documentation
accuracy and production operational readiness remain unverified.

## Provenance

Adapted from [Hema Kalyan's Doclify](https://github.com/KalyanM45/Doclify), revision
`93dfd6632929e0b1dc4b10b1ff0f2115aa890d01`, selected through
[AI Project Gallery](https://github.com/KalyanM45/AI-Project-Gallery).
Upstream Git history and the original [AGPLv3 license](LICENSE) are preserved.
Modified by Sushant Nemade on 2026-10-13; see [source notices](NOTICE.md).
The original documentation is retained as [upstream history](docs/UPSTREAM_README.md),
not current instructions for this derivative.

Primary category: **Data and Developer Tools**. Portfolio placement:
**Trustworthy data and developer tools**.
[Projects catalog](https://github.com/Sushant-Nemade/ai-project-gallery).

## Quick Start

Requires Python 3.10 or newer and uv. Local validation uses Python 3.13.
The distribution is **doclify-portfolio 0.3.0**; the command remains `doclify`.
This is not the upstream PyPI package and no PyPI publishing is configured.

```text
git clone https://github.com/Sushant-Nemade/doclify.git
cd doclify
uv sync --frozen --extra dev
uv run --frozen --extra dev doclify --help
uv run --frozen --extra dev doclify --license
```

For a complete offline example on Windows PowerShell:

```powershell
Set-Location examples/tiny_project
& ../../.venv/Scripts/doclify.exe init
& ../../.venv/Scripts/doclify.exe run --dry-run
& ../../.venv/Scripts/doclify.exe run --offline
```

On Linux/macOS, use `../../.venv/bin/doclify` from the same example directory.
Offline output is labeled structural extraction, not AI-generated insight.
No project code is executed and no provider requests are made in offline mode.

## Review And Publish

A run prints the private Markdown artifact path and its SHA-256 digest.
Open that artifact, inspect the full content, then approve the exact digest:

```text
doclify publish --approve FULL_REVIEWED_DIGEST
```

This writes `README.generated.md`, preserving `README.md`. Only an explicit
`--replace-readme` option backs up and replaces the existing README. The command
rejects modified drafts and changed source files. Individual file replacement is
atomic; multi-file publication is not falsely described as a transaction.

## Configured AI Generation

Review the `structure` list in `doclify.yaml` and run a dry-run first. Configure
`GROQ_API_KEY` locally, never in chat or Git, then explicitly consent to uploading
the selected source code:

```text
doclify run --allow-upload
doclify update src/module.py --allow-upload
doclify update . --offline
doclify models
doclify set default llama-3.3-70b-versatile
```

`models` explicitly contacts Groq. `update .` reuses valid summaries but still
performs final synthesis; it is not a no-API shortcut. Provider terms, quotas and
costs apply. No paid services, telemetry or scheduled uploads are activated.

## Architecture And Improvements

```text
init -> reviewed manifest -> bounded UTF-8 extraction
     -> source/prompt/model fingerprint -> cached file summaries
     -> bounded final synthesis -> private content-addressed draft
     -> human review + digest/source checks -> safe publication
```

- Nested Git ignore rules, private-file exclusions, root-contained paths and
  symlink/junction rejection restrict discovery and processing.
- Strict YAML/Pydantic validation rejects duplicate paths/keys, unknown fields
  and unbounded provider settings. Notebook outputs are excluded.
- Hash-based summaries avoid reprocessing unchanged files; failed/corrupt state
  is not silently erased. Concurrent cooperating writers are excluded.
- Fixed-origin Groq calls have finite timeouts, retry/token/request limits and
  redacted failure messages. Empty/truncated output returns a nonzero CLI exit.
- Prompt templates, license and modification notices are bundled in the wheel;
  the source archive includes tests and build instructions.

Secret screening is incomplete: manually inspect source before upload. Generated
claims still require review. This is a trusted local-directory tool, not a
multi-user service, an adversarial filesystem sandbox or a factual guarantee.

## Verification

From the repository root:

```text
uv run --frozen --extra dev pytest -q
uv run --frozen --extra dev ruff check .
uv run --frozen --extra dev ruff format --check .
uv run --frozen --extra dev python -m build
uv run --frozen --extra dev python -m scripts.verify_release
uv run --frozen --extra dev python -m twine check dist/*
uv run --frozen --extra dev pip-audit --local --skip-editable --progress-spinner off
```

CI checks Linux Python 3.10/3.13 and Windows Python 3.13 without live credentials.
It produces source/wheel artifacts, not upstream PyPI releases. See
[release evidence](docs/RELEASE_STATUS.md) and [operations](docs/OPERATIONS.md).