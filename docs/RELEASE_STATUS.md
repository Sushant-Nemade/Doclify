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

## Release Gates

Frozen-lock tests, lint, formatting, dependency audit, installed-wheel CLI checks,
distribution metadata and remote CI must pass before catalog promotion. Exact
final results and remote run links are recorded after those gates execute.

## Not Verified

Live Groq access/model availability, generated-documentation accuracy and
adversarial prompt-injection resistance. There is no hosted AI service or public
interactive demo; examples are deterministic local references. Cross-platform
results are pending until remote CI completes. This is not production
certification, clinical/financial advice, a privacy guarantee or an uptime SLA.