# Release Status

Version: doclify-portfolio 0.3.0. Modified-source date: 2026-10-13.
Upstream: KalyanM45/Doclify at 93dfd6632929e0b1dc4b10b1ff0f2115aa890d01.
License: original GNU AGPLv3 retained; modification/source notices included.

## Verified Locally

- Windows Python 3.13: 39 automated cases passed; one symlink-creation case
  skipped because this host does not permit unprivileged symbolic links.
- Credential-free, side-effect-free help and dry-run; strict configuration and
  nested ignore checks; path/size/binary/credential screening.
- Offline generation, cache reuse and source invalidation, targeted updates,
  preserved prior drafts on provider failures, reviewed publication and backup.
- Real Groq SDK request construction via HTTPX MockTransport: fixed origin,
  token bounds, failure redaction and disabled redirects. No live inference.
- Wheel/source builds include prompts, license, notices and build/test material.

## Passed Release Gates

Frozen-lock tests, lint, formatting, installed-wheel offline CLI checks and
distribution metadata passed locally. Dependency auditing reported no known
vulnerabilities after updating affected lockfile entries, including the
Linux-only cryptography dependency.

[Verify Doclify run 38473880068](https://github.com/Sushant-Nemade/Doclify/actions/runs/38473880068)
passed on source revision `56568cc947d45181ff803bafad689096724e4179`:
Linux Python 3.10, Linux Python 3.13 and Windows Python 3.13. The Linux 3.13 job
also passed dependency auditing and uploaded the source/wheel artifacts.
The current run on any later documentation-only revision remains authoritative.

## Not Verified

Live Groq access/model availability, generated-documentation accuracy and
adversarial prompt-injection resistance. There is no hosted AI service or public
interactive demo; examples are deterministic local references. This is not
production certification, clinical/financial advice, a privacy guarantee or an
uptime SLA.