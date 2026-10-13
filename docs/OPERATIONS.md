# Operations and Boundaries

## Local installation

The derivative distribution is doclify-portfolio 0.3.0, not the upstream PyPI
package. The CLI remains doclify. Python 3.10 is the minimum; local verification
uses Python 3.13. CI checks Linux 3.10/3.13 and Windows 3.13.

Install uv, clone the public source, then run `uv sync --frozen --extra dev`.
Invoke `uv run --frozen --extra dev doclify --help` from this checkout.
To document a different directory with the installed environment, invoke the
checkout's `.venv/Scripts/doclify.exe` on Windows or `.venv/bin/doclify` on Unix
while your shell is in that directory. Do not install upstream `pip install doclify`
and assume it includes these modifications.

## Inspect before upload

`doclify init` creates a source manifest and appends private-state entries to
.gitignore while preserving its original contents. It never executes repository
code. Inspect doclify.yaml, then run `doclify run --dry-run`. A dry-run validates
paths, text and budgets without writes or network requests.

`doclify run --offline` uses deterministic line counts and Python AST definitions.
It is a working structural reference, not simulated AI inference. A Groq run needs
`doclify run --allow-upload` and a locally configured GROQ_API_KEY. A local .env
file is read only when a Groq request is explicitly invoked; values are not
interpolated and provider exceptions are not printed. Source is sent to Groq:
verify applicable company policy, user consent, provider terms and privacy rules.
No telemetry, paid hosting or scheduled uploads are configured.

Secret screening is conservative and incomplete, not a guarantee. Manually review
the selected source even if screening passes. Notebook outputs are excluded.
Unsupported/binary/oversized files, ignored directories, private filenames,
symlinks, Windows junctions and out-of-root paths are rejected. Reads are bounded
to 256 KB per file and 2 MB per project; discovery is capped at 128 sources and
10,000 entries. Context uses character bounds, not exact model-token accounting.

## Generation and cache

Each file is summarized in bounded chunks, then a final call receives only the
summaries. Cache entries include source SHA-256 and a fingerprint of provider,
model, limits, prompt content and extraction version. Unchanged entries are reused;
deleted entries are pruned. `doclify update src/module.py` refreshes that manifest
selection and refuses unrelated stale entries. `doclify update .` refreshes all
stale files and still performs final synthesis; it is not a no-API command.

The default limit is 32 logical requests, one retry per logical request, a
30-second SDK timeout and 2,048 maximum output tokens. The dry-run report bounds
HTTP attempts including SDK retries. It is not a dollar estimate or a strict
whole-operation wall-clock deadline. Authentication/model errors terminate the
run; only SDK-designated retryable failures are retried. Truncated and empty
outputs fail closed. Inspect generated claims; model output is not factual proof.

Corrupt or old-format cache data is preserved, not silently reset. Back up and
restore or remove .doclify/cache.json explicitly. Partial successful summaries
may remain cached after a later provider failure. No new draft is promoted until
final synthesis succeeds; an older reviewed draft is not erased.

## Review and publication

A successful run produces an immutable-name Markdown artifact under
.doclify/generated_artifacts and a draft.json pointer with its SHA-256 digest.
Inspect the actual artifact before `doclify publish --approve FULL_DIGEST`.
The digest checks the exact draft bytes, and selected source hashes must still
match. Default publication writes README.generated.md, not your README.md.
Only `--replace-readme` backs up and replaces README.md. Backups are content-addressed
under .doclify/backups. Changing a draft or source requires regeneration/review.

Each file replacement is atomic. Cache, draft pointer, backup and publication
are not a multi-file transaction. A filesystem error can leave an unreferenced
artifact or backup; it must not report publication success. Restore a backup by
reviewing its contents and replacing README.md yourself. Keep private state out
of Git and use independent backups for disaster recovery.

.doclify/pipeline.lock excludes cooperating writers. After an interrupted process,
confirm no Doclify process is active before removing a stale lock. This local CLI
assumes a trusted, user-owned project directory: it is not a sandbox against an
attacker concurrently replacing directories or source files. File permissions
use owner-only creation where supported, but Windows ACLs need independent review.

## Build and source availability

Run `uv run --frozen --extra dev pytest -q`, `ruff check .`, `ruff format --check .`,
`python -m build`, `python -m scripts.verify_release` and `python -m twine check dist/*`
with the uv environment. The release checker installs the wheel into a temporary
target and exercises its bundled resources and offline CLI outside the checkout.
The source archive contains tests, prompts, build scripts and operations docs.
CI artifacts are source/wheel downloads, not PyPI publication.

The GNU AGPLv3 license and upstream notices are preserved. `doclify --license`
links the complete public modified source and license. Any later network-hosted
version must prominently offer its corresponding source as required by the AGPL.
No network service or hosted AI endpoint is included in this release.