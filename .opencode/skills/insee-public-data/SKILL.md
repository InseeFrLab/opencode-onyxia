---
name: insee-public-data
description: Find and load French public data — Insee datasets (census, SIRENE, BDM macroeconomic series, local data), data.gouv.fr catalogs, and official geographic reference data (COG) — from Python, R, or via the datagouv MCP server. Prefers Parquet distributions and direct-to-duckdb ingestion. Use when the user needs an external/public dataset, an Insee series, or French administrative reference data. (keywords: données publiques, open data, recensement, communes, code officiel géographique, série)
license: MIT
---

# Sourcing French public data (Insee, data.gouv.fr)

Order of preference: **Parquet distribution read lazily** (duckdb/arrow over
HTTPS or S3) → dedicated API client (`pynsee`, R `insee`) → CSV download (last
resort — convert to Parquet immediately, see `onyxia-storage-s3`).

## 1. Parquet-first: query files in place

Several flagship datasets are published as Parquet on data.gouv.fr /
static mirrors (e.g. SIRENE, DVF property transactions, census extracts).
duckdb reads them over HTTPS without downloading:

```sql
INSTALL httpfs; LOAD httpfs;
SELECT dep, count(*) FROM read_parquet('https://<direct-parquet-url>') GROUP BY 1;
```

If several analyses will hit the same file, copy it **once** to your S3 bucket
(`aws s3 cp` / `COPY ... TO 's3://...'`), then work from S3.

## 2. Finding datasets

- **datagouv MCP server** (`https://mcp.data.gouv.fr/mcp`): pre-declared but
  disabled in `opencode.jsonc`. Enable it per-project (never globally) with an
  `opencode.json` at the repo root:
  ```json
  { "mcp": { "datagouv": { "type": "remote", "url": "https://mcp.data.gouv.fr/mcp", "enabled": true } } }
  ```
  ⚠️ A remote MCP sends conversation context outside the platform — public
  data queries only. Once enabled, use it to search datasets/resources and get
  direct file URLs (prefer resources with `format: parquet`).
- Without MCP: the data.gouv.fr **tabular API** and catalog search
  (`https://www.data.gouv.fr/api/1/datasets/?q=...`) — `curl` requires user
  confirmation, which is expected.
- Insee's own catalog: https://www.insee.fr/fr/statistiques (files) and the
  APIs below.

## 3. Insee APIs from code

**Python — `pynsee`** (`uv pip install pynsee`):

```python
from pynsee.macrodata import get_series          # BDM macroeconomic series
from pynsee.localdata import get_local_data      # local/communal statistics
from pynsee.geodata import get_geodata           # geographies (Admin Express)
from pynsee.sirene import search_sirene          # SIRENE business register

df = get_series("001769682")                     # e.g. monthly CPI
```

`pynsee` needs an API key from https://portail-api.insee.fr for most modules
(store it in Vault, inject as env var — see `vault-secrets-onyxia`).

**R — `insee` package** (BDM series, no key needed for basic use):

```r
library(insee)
idbank_list <- get_idbank_list("CNA-2014-PIB")   # find series ids
df <- get_insee_idbank("001769682")
```

**Geographic reference (COG — Code officiel géographique)**: in R use
`COGugaison`/`insee`; in Python `pynsee.localdata.get_area_list()`. For
commune boundaries: Admin Express via `get_geodata` or IGN downloads.

## 4. SSP Cloud shared datasets

Some reference datasets are already mirrored on the platform's MinIO —
check before re-downloading:

```bash
aws --endpoint-url "https://$AWS_S3_ENDPOINT" s3 ls s3://donnees-insee/ 2>/dev/null \
  || echo "bucket not accessible from this account"
```

`diffusion/` folders in any user bucket are public-readable too — a teammate
may already have staged the file (see `onyxia-storage-s3`).

## 5. Hygiene

- Record the **exact source URL + retrieval date** in the README or the
  ingestion script; public files move and get revised.
- Don't commit downloaded data (see `git-workflow-ds`); land it on S3 with a
  parameterized path.
- Watch encodings and department codes (`2A`, `2B`, leading zeros): read codes
  as **text**, never integers.
