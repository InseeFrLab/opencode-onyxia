---
name: mlflow-docs
description: Look up the official MLflow documentation (features, APIs, tracing, evaluation, integrations) from mlflow.org via its llms.txt index. Use when the user asks how an MLflow API works or for MLflow doc examples. The llms.txt index covers GenAI topics; for classic tracking, see mlflow-tracking.
license: Apache-2.0
metadata:
  upstream: mlflow/skills@6303169
  adapted: onyxia
---

# MLflow documentation search

Needs outbound HTTPS to `mlflow.org` (public documentation; no data is sent). If the fetch is refused or fails,
say so and answer from the installed package (`help()` / `inspect`) instead of guessing.

## Workflow

1. Fetch the index `https://mlflow.org/docs/latest/llms.txt` with the `webfetch` tool and find the page(s)
   relevant to the topic.
2. Fetch the `.md` source of that page (`https://mlflow.org/docs/latest/<path>.md`).
3. Present the result with **verbatim** code examples, then adapt them to the project (tracking URI from
   `MLFLOW_TRACKING_URI`, models from the self-hosted gateway).

## Anti-patterns

- Do not fetch `.html` pages: use the `.md` sources only.
- Do not use web search: start from `llms.txt` (search returns outdated or third-party content).
- Do not ask vaguely ("extract the documentation"): ask for the code blocks verbatim, without summarising.
- Do not use versioned paths (`/docs/3.8/`) unless the user explicitly requests a version: use `/docs/latest/`.
- Do not guess URLs: verify the path exists in `llms.txt` before fetching.
- Do not follow external links (GitHub, PyPI, third parties) and do not mix in other libraries' docs.
- `llms.txt` indexes the GenAI documentation only; for classic ML tracking pages the paths may differ.
- The docs describe the latest MLflow: check the server and client versions (see `mlflow-tracking`) before
  using an API.
