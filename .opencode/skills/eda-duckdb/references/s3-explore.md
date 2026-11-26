# Explore S3/MinIO with DuckDB — listing, metadata, any-format reader

> Recipes adapted from the `s3-explore` and `read-file` skills of
> [duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills) (MIT) — see `THIRD_PARTY.md`.
> Rewritten for Onyxia/MinIO and corrected where upstream was wrong (all tested on DuckDB 1.5.6, SSP Cloud).

## 1. Which credentials does DuckDB use? (check before blaming the data)

Onyxia services pre-provision a **persistent secret** `s3_onyxia_connection` (scope `s3://`), so in the DuckDB
CLI a plain `s3://...` path usually works with no `CREATE SECRET`. Inspect it (values are redacted):

```sql
SELECT name, persistent, scope FROM duckdb_secrets();
SELECT name FROM which_secret('s3://<bucket>/<path>', 's3');   -- which secret serves this path
```

- A 403 after days = expired/rotated token → see `onyxia-storage-s3` (`scripts/check_s3.sh`), then create a fresh
  temporary secret from the environment (`eda-duckdb` section 1).
- **Do not** create an S3 secret with `PROVIDER credential_chain` alone, nor an unscoped `PROVIDER config`/region
  secret (upstream's examples): it ignores `AWS_S3_ENDPOINT`/path-style or targets AWS and **shadows the working
  platform secret** (`403 ... in region 'us-west-2'`). `credential_chain` is fine **with**
  `ENDPOINT getenv('AWS_S3_ENDPOINT'), URL_STYLE 'path'`.
- Public data on a *non-Onyxia* bucket (e.g. Overture Maps): see `geodata/references/duckdb-spatial.md` for the
  scoped anonymous secret (empty keys) — never an unscoped one.

## 2. What is in this prefix? (metadata only, nothing is downloaded)

```sql
-- names only
SELECT file FROM glob('s3://<bucket>/<prefix>/*') LIMIT 50;
-- names + size + date: select ONLY these columns, never `content` (that would download the files)
SELECT filename, (size / 1024 / 1024)::DECIMAL(10,1) AS size_mb, last_modified
FROM read_blob('s3://<bucket>/<prefix>/*') ORDER BY filename LIMIT 50;
```

Sharing convention: `s3://<bucket>/diffusion/` is readable by every Onyxia user (see `onyxia-storage-s3`).

## 3. Parquet without reading the data

```sql
-- exact row count (footer only)
SELECT sum(num_rows) AS rows, count() AS files FROM parquet_file_metadata('s3://<bucket>/<path>/*.parquet');
-- compressed size = sum over column chunks
SELECT sum(total_compressed_size) / 1024 / 1024 AS compressed_mb
FROM parquet_metadata('s3://<bucket>/<path>/*.parquet');
-- schema
SELECT name, type FROM parquet_schema('s3://<bucket>/<path>/one-file.parquet');
```

> ⚠ `parquet_metadata()` returns **one row per column chunk**. Upstream's
> `sum(row_group_num_rows)` over it counts every row once per column (1000 rows × 3 columns reported as 3000).
> Use `parquet_file_metadata` for rows, as above.

## 4. Preview any file, any format: `read_any`

Define once per session; works on local paths and `s3://` (extension picks the reader).

```sql
INSTALL excel; LOAD excel;   -- only if you need .xlsx
CREATE OR REPLACE MACRO read_any(file_name) AS TABLE
  WITH csv_case     AS (FROM read_csv(file_name))
     , json_case    AS (FROM read_json_auto(file_name))
     , parquet_case AS (FROM read_parquet(file_name))
     , excel_case   AS (FROM read_xlsx(file_name))
  FROM query_table(
    CASE
      WHEN file_name ILIKE '%.csv' OR file_name ILIKE '%.tsv' OR file_name ILIKE '%.txt' THEN 'csv_case'
      WHEN file_name ILIKE '%.json' OR file_name ILIKE '%.jsonl' OR file_name ILIKE '%.ndjson' THEN 'json_case'
      WHEN file_name ILIKE '%.parquet' OR file_name ILIKE '%.pq' THEN 'parquet_case'
      WHEN file_name ILIKE '%.xlsx' THEN 'excel_case'
    END);

DESCRIBE FROM read_any('<path>');
SELECT count() FROM read_any('<path>');
FROM read_any('<path>') LIMIT 20;
```

`Binder Error: Cannot use NULL as function argument` = unsupported extension: call the right `read_*` directly.
Spatial files → `geodata`; notebooks (`.ipynb`) are JSON: `read_json_auto` then `UNNEST(cells)`.

## 5. Then
Analytical questions → `friendly-sql.md` and `safe-query.md` (bound the output first). Profiling →
`eda-duckdb` sections 2-3 or `scripts/profile_parquet.py`. Conversions → `convert.md`.
