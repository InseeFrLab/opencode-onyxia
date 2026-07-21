---
description: Scaffold a reproducible data science project (R or Python) following SSP Cloud conventions
agent: build
---

Scaffold a reproducible data science project in the current directory,
following the platform conventions (AGENTS.md and the skills mentioned below).

Requested by the user: $ARGUMENTS

Steps — ask about anything not already specified in the request above:

1. **Clarify** (one question, only if not deducible): language (Python or R),
   project name, and whether a Quarto report stub is wanted.
2. **Initialize Git** if not already a repo, with the data-science `.gitignore`
   from the `git-workflow-ds` skill (data/, environments, outputs, .env).
3. **Language setup**
   - Python: `uv init` (pyproject.toml + uv.lock), a `src/<pkg>/` layout,
     `ruff` and `pytest` configured in pyproject.toml, `tests/` with one
     passing placeholder test — follow the `python-datascience` skill.
   - R: `renv::init()`, `R/` for functions, `tests/testthat/` with one passing
     placeholder test, lintr/styler defaults — follow the `r-datascience` skill.
4. **Data conventions**: create `conf/config.yaml` with a parameterized S3
   path (`s3://<bucket>/...` placeholder, endpoint from `AWS_S3_ENDPOINT`) and
   a data-access stub following the `onyxia-storage-s3` skill. No data in Git.
5. **Notebook hygiene**: install the nbstripout Git filter — run the
   `git-workflow-ds` skill's `scripts/setup-nbstripout.sh` (Python projects, or
   whenever notebooks are expected).
6. **README.md**: project purpose, how to restore the environment
   (`uv sync` / `renv::restore()`), how to run tests, where the data lives (S3
   path, retrieval date), how to render the report if any.
7. **Optional Quarto stub**: if wanted, add a parameterized report from the
   `quarto-publication` skill's `assets/report-template.qmd`.
8. **First commit**: atomic, message per `git-workflow-ds` conventions.
   Show `git status` first so the user can confirm nothing unwanted is staged.

Finish by printing the created tree and the next manual steps (e.g. create the
remote repo, store any API key in Vault — `vault-secrets-onyxia` skill).
