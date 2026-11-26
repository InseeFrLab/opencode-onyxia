# Third-party content

Some skills and references in `.opencode/skills/` are adapted from two upstream open-source projects. Upstream
licenses are kept in [`licenses/`](licenses/); the exact revisions are pinned in [`UPSTREAM.lock`](UPSTREAM.lock).
Everything else in this repository is under the repository [LICENSE](LICENSE) (MIT).

## 1. duckdb/duckdb-skills — MIT

- Source: <https://github.com/duckdb/duckdb-skills> @ `44dfbbb414e54187964a2212eae28495f6ae21d9` (2026-11-17)
- License: MIT, Copyright 2018-2025 Stichting DuckDB Foundation — [`licenses/duckdb-skills.LICENSE`](licenses/duckdb-skills.LICENSE)
- Upstream is a Claude Code plugin; its skills were **adapted by hand** (not copied verbatim), because they
  assume AWS credentials, Claude-specific argument syntax and cross-references, and a recent DuckDB.

| Upstream skill | Adapted into | Main changes |
|---|---|---|
| `query` | `eda-duckdb/references/friendly-sql.md`, `eda-duckdb/references/safe-query.md` | Friendly-SQL cheat sheet (fixed: dot-chaining on bare string literals does not parse on DuckDB 1.5); result-size guard tied to the 200-line tool-output cap; sandboxed mode extended to S3 (persistent secrets must be disabled before locking) |
| `s3-explore`, `read-file` | `eda-duckdb/references/s3-explore.md` | Onyxia/MinIO credentials (upstream `PROVIDER credential_chain` alone fails on MinIO and shadows the platform secret); fixed the Parquet row count (`parquet_metadata` is one row per column chunk) |
| `convert-file` | `eda-duckdb/references/convert.md` | Parquet-first, S3 output, `diffusion/` warning |
| `spatial` (references) | `geodata/references/duckdb-spatial.md` | French CRS (Lambert-93), scoped anonymous Overture secret with empty keys (the MinIO env keys otherwise leak to AWS), `aws` CLI endpoint override, current Overture places schema (`taxonomy`/`basic_category`, not `categories`) |
| `duckdb-docs` | `duckdb-docs/SKILL.md`, `duckdb-docs/scripts/search_docs.py` | Reimplemented as a script run with a recent DuckDB through `uv` (the hosted index cannot be opened by the preinstalled 1.5 CLI); BM25 query rewritten for DuckDB 2.x; local-catalog tier added |
| `install-duckdb`, `attach-db`, `read-memories` | not adopted | DuckDB is preinstalled; `attach-db` stores secrets in a state file; `read-memories` reads Claude Code logs |

## 2. mlflow/skills — Apache-2.0

- Source: <https://github.com/mlflow/skills> @ `630316930230d971e3c555c0be0279506a91c069` (2026-11-04)
- License: Apache License 2.0 — [`licenses/mlflow-skills.LICENSE`](licenses/mlflow-skills.LICENSE). The upstream
  repository ships no `NOTICE` file.
- **Modified files (Apache-2.0 §4b):** every vendored file below was changed by
  [`scripts/vendor_mlflow_skills.py`](scripts/vendor_mlflow_skills.py), which re-creates them from the pinned revision
  (run `python3 -I scripts/vendor_mlflow_skills.py`; it asserts each edit still applies).

| Vendored skill | Upstream path | Changes |
|---|---|---|
| `mlflow-docs` | `mlflow-docs/` | Rewritten for opencode's `webfetch` tool; offline behaviour; version note |
| `mlflow-trace-instrumentation` | `mlflow-trace-instrumentation/` | Removed Databricks/Unity Catalog and TypeScript content; Onyxia prerequisites (MLflow >= 3 server check, self-hosted gateway, `mlflow.openai.autolog()`) |
| `mlflow-trace-retrieval` | `mlflow-trace-retrieval/` | Removed Databricks/Unity Catalog steps; prerequisites |
| `mlflow-trace-analysis` | `mlflow-trace-analysis/` | Removed Databricks specifics and the Codex `agents/openai.yaml`; references to skills not vendored replaced |
| `mlflow-evaluation` | `mlflow-evaluation/` | Removed Databricks/Unity Catalog/online-monitoring content; judges restricted to the self-hosted gateway (no external providers); references to skills not vendored replaced |

Not adopted: `mlflow-agent` (dispatcher that forbids doing the work itself), `mlflow-onboarding`,
`mlflow-sagemaker`, `mlflow-trace-metrics`, `mlflow-agent-improvement`, and the Claude Code `hooks/`.

Each vendored `SKILL.md` records `license: Apache-2.0` and `metadata.upstream` in its frontmatter.
Classic experiment tracking (parameters, metrics, registry) stays with this repository's own `mlflow-tracking` skill.

## Updating

1. Review the upstream diff (`https://github.com/<owner>/<repo>/compare/<pinned-sha>...main`).
2. Bump the SHA in `UPSTREAM.lock`.
3. MLflow: re-run `scripts/vendor_mlflow_skills.py` (fix any edit that no longer applies), review `git diff`.
   DuckDB: port the relevant upstream changes into the adapted files by hand and re-test the snippets.
4. Update the SHA and date in this file.
