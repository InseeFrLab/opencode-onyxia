# Project context — Data science on Onyxia

This repository is worked on from an interactive service (VSCode, Jupyter or RStudio)
launched on **Onyxia** — the data science platform developed by Insee,
deployed here on the **SSP Cloud** (`datalab.sspcloud.fr`). All agents
must know and leverage this environment rather than proposing
"generic cloud" solutions.

## Guiding principles
- **Reproducibility first**: everything must be replayable identically
  (lockfiles, containers, declarative pipelines, data on S3, code under Git).
- **Open source**: R, Python, Quarto, Git; no proprietary dependency.
- **Confidentiality**: on the public instance, only public / non-sensitive
  data is allowed. Never write a secret in plain text in the code.
  The LLMs used here are **self-hosted on the platform**: data sent
  to the agents stays within the sspcloud perimeter.
- **From prototype to production**: we target the full MLOps cycle
  (experimentation → packaging → deployment → monitoring).

## Platform: what is already provided and preconfigured
- **Kubernetes** underneath; each service is a *Helm chart* from the catalog
  (`inseefrlab/...`). Two URL conventions coexist:
  - `https://user-<namespace>-<id>.user.lab.sspcloud.fr`: **auto-generated** URL
    of a service launched from the catalog (MLflow, VSCode, Jupyter…);
  - `https://<chosen-name>.lab.sspcloud.fr`: hostname **declared yourself** in
    a custom `Ingress` (e.g. prediction API deployed via GitOps with ArgoCD).
- **S3 storage = MinIO** (compatible with Amazon's S3 API). The personal bucket
  is named after the username. The `diffusion/` folder at the root of a bucket
  is **readable by all** users (sharing mechanism).
- **Vault** for secrets (tokens, passwords), injected as environment
  variables into services (details in the `vault-secrets-onyxia` skill).
- **MLflow**: shared instance for experiment tracking and the model
  registry (metadata in PostgreSQL, artifacts on MinIO).
- **Argo Workflows** (orchestration of parallel tasks on K8s) and **ArgoCD**
  (continuous deployment via GitOps) for industrialization.
- **duckdb** available in all interactive services; prefer it for
  processing large data (Parquet, lazy reading).

## Automatically injected environment variables
READ from the environment, NEVER hard-code:

| Variable | Role |
|---|---|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | temporary S3/MinIO token |
| `AWS_DEFAULT_REGION` | region (often `us-east-1` on the MinIO side) |
| `AWS_S3_ENDPOINT` | MinIO host (e.g. `minio.lab.sspcloud.fr`) |
| `MLFLOW_TRACKING_URI` | set when an MLflow service is running |
| `MLFLOW_S3_ENDPOINT_URL` | S3 endpoint for MLflow artifacts |
| `VAULT_ADDR`, `VAULT_TOKEN` | access to the Vault server (secrets) |
| `VAULT_MOUNT`, `VAULT_TOP_DIR` | mount point and root folder of your secrets (`vault-secrets-onyxia` skill) |

> **S3 token expiration (7 days)**: an expired token causes a **403** error
> on MinIO and the service shows up in red in "My services". Remedies:
> relaunch a service (new token) or re-inject fresh tokens. If an agent
> sees a 403 on S3, suspect expiration before any other diagnosis.

## Data access (summary — details in the `onyxia-storage-s3` skill)

SSP Cloud MinIO endpoint: `https://minio.lab.sspcloud.fr` (= `$AWS_S3_ENDPOINT`).
**Onyxia rule**: do not download files into the container, **ingest the
data directly into memory** from S3; only copy locally if necessary.

- **Python**: `s3fs` to read/write in memory; `duckdb` for large
  Parquet (lazy reading, *predicate pushdown*).
- **R**: `duckdb` (reading Parquet/dataset on S3) or `aws.s3` (the AWS_* variables suffice).
- **Terminal**: **`aws s3`** is the preferred CLI (the `mc` client also exists):
  `aws --endpoint-url "https://$AWS_S3_ENDPOINT" s3 ls s3://$USERNAME/`.

## Expected working conventions
- Python: project managed with **`uv`** (`pyproject.toml` + `uv.lock`), formatted/linted
  with **`ruff`**, tested with **`pytest`**. Prefer `polars`/`duckdb` for large data volumes.
- R: environment pinned with **`renv`**, pipelines with **`targets`** only if strictly necessary, tests with
  **`testthat`**, `tidyverse`/`styler` style.
- Data: no large files in Git → everything on S3; parameterized paths.
- Documentation and reporting: **Quarto**.
- No secret committed. No data in the repository.

## Internal references (authoritative)
- SSP Cloud platform docs: https://docs.sspcloud.fr
- Onyxia user guide: https://docs.onyxia.sh/user-doc/user-guide
- **R** — utilitR (Insee best practices): https://book.utilitr.org
- **Python** — "Python pour la data science" (Python for data science, L. Galiana): https://pythonds.linogaliana.fr
- MLOps: https://github.com/InseeFrLab/formation-mlops
- Production deployment / reproducibility: https://ensae-reproductibilite.github.io/website
- Data science Docker images: https://github.com/inseefrlab/images-datascience

When a task falls within a tooled domain, **load the corresponding skill**
(`onyxia-storage-s3`, `mlflow-tracking`, `argo-mlops`, `r-datascience`,
`python-datascience`, `onyxia-reproducibility`, `quarto-publication`,
`vault-secrets-onyxia`, `git-workflow-ds`) before producing code.
