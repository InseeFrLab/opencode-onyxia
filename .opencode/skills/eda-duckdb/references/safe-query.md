# Safe, bounded DuckDB queries

> Sandbox pattern and result-size guard adapted from the `query` skill of
> [duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills) (MIT) — see `THIRD_PARTY.md`.
> The S3 variant and the Onyxia specifics below were tested on an SSP Cloud service (DuckDB 1.5.6).

## 1. Keep the output small (do this before every query on a big source)

The tool output is truncated at 200 lines / 20 KB and **the head is kept**, so an unbounded `SELECT *` both
wastes context and loses the interesting part. Before running a query on a large source:

1. **Estimate the size without scanning the data.**
   Parquet: `SELECT sum(num_rows) AS rows FROM parquet_file_metadata('s3://<bucket>/<path>/*.parquet');`
   CSV/JSON: `SELECT count() FROM 'file.csv';` (one scan).
2. **Bound the result**: an aggregation, `LIMIT 20`, `USING SAMPLE 1000 ROWS`, or `SUMMARIZE`.
   Rule of thumb: a source with **more than ~1M rows and no aggregation/`LIMIT` is never run as is** —
   rewrite the query or ask the user.
3. **Wide results**: select the needed columns only (`SELECT * EXCLUDE (...)`); for a big result needed later,
   write it to a file (`COPY (...) TO 'out.parquet' (FORMAT parquet)`) and show `LIMIT 20` of it.
4. Skip the check for intrinsically bounded statements (`DESCRIBE`, `SUMMARIZE`, `count()`, aggregations).

## 2. Sandboxed mode — query an untrusted or one-off file, nothing else reachable

Use when the SQL or the file comes from somewhere you do not control, or to prove a query only touches one input.
The order matters; the last `SET` makes the configuration immutable for the session.

```bash
duckdb :memory: -csv <<'SQL'
SET allowed_paths=['/abs/path/data.csv'];   -- the ONLY file readable
SET enable_external_access=false;           -- no other file, no network
SET allow_persistent_secrets=false;         -- do not load stored credentials
SET lock_configuration=true;                -- settings can no longer be changed
SELECT count() AS n FROM '/abs/path/data.csv';
SQL
```

Verified behaviour: the allowed file is readable; any other path fails with `Permission Error: Cannot access
file ... disabled by configuration`; `SET enable_external_access=true` afterwards fails with
`the configuration has been locked`.

### Sandboxed S3 read (one prefix only)

`allow_persistent_secrets=false` also disables the platform's pre-provisioned `s3_onyxia_connection` secret,
so create a temporary one from the environment — **before** locking:

```bash
duckdb :memory: -csv <<'SQL'
LOAD httpfs;
SET allow_persistent_secrets=false;
CREATE OR REPLACE SECRET onyxia (TYPE S3, PROVIDER credential_chain,
    ENDPOINT getenv('AWS_S3_ENDPOINT'), URL_STYLE 'path');
SET allowed_directories=['s3://<bucket>/<prefix>/'];
SET enable_external_access=false;
SET lock_configuration=true;
SELECT count() FROM read_parquet('s3://<bucket>/<prefix>/*.parquet');
SQL
```

Verified: the in-scope prefix is readable and another bucket fails with the same `Permission Error`.
If you skip `SET allow_persistent_secrets=false`, the lock makes DuckDB fail while loading the stored secret file.

## 3. Pitfalls
- A sandbox limits *where* DuckDB can read/write, not how much it computes: still apply section 1.
- Heredoc with a quoted delimiter (`<<'SQL'`) for multi-line SQL: no shell expansion, no quoting accidents.
- Never put credentials in the SQL text: use `getenv()` (see `eda-duckdb` section 1); never write them to a file.
