# Convert data files with DuckDB (Parquet first)

> Adapted from the `convert-file` skill of [duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills)
> (MIT) — see `THIRD_PARTY.md`. Local conversions were tested on DuckDB 1.5.6.

Reproducibility default: convert CSV/Excel/JSON inputs to **Parquet (zstd)** early, keep the source untouched,
write the result next to the pipeline outputs (parameterised paths, never a hard-coded bucket).

## Read -> write (one statement)

```sql
-- CSV / JSON / Excel -> Parquet
COPY (SELECT * FROM read_csv('in.csv')) TO 'out.parquet' (FORMAT parquet, COMPRESSION zstd);
COPY (SELECT * FROM read_json_auto('in.json')) TO 'out.parquet' (FORMAT parquet, COMPRESSION zstd);
INSTALL excel; LOAD excel;
COPY (SELECT * FROM read_xlsx('in.xlsx')) TO 'out.parquet' (FORMAT parquet, COMPRESSION zstd);

-- Parquet -> CSV / JSON / Excel (for people who need them)
COPY (SELECT * FROM 'in.parquet') TO 'out.csv' (HEADER, DELIMITER ',');
COPY (SELECT * FROM 'in.parquet') TO 'out.json' (ARRAY true);          -- JSON array; omit ARRAY for JSON Lines
COPY (SELECT * FROM 'in.parquet') TO 'out.xlsx' (FORMAT xlsx, HEADER true);   -- needs the excel extension
```

- Partitioned dataset: `COPY (...) TO 'out_dir' (FORMAT parquet, PARTITION_BY (year, region), COMPRESSION zstd)`.
- Existing target: DuckDB refuses to overwrite a non-empty partitioned directory; choose a new path rather than
  adding `OVERWRITE`/`OVERWRITE_OR_IGNORE` blindly. Never overwrite the input file.
- Typing: check `DESCRIBE` first (dates as strings, codes that lost leading zeros) and cast explicitly in the
  `SELECT` (`SELECT * REPLACE (code::VARCHAR AS code)`), or pass `read_csv(..., types = {'code': 'VARCHAR'})`.
- Check the result: `SELECT count() FROM 'out.parquet'` equals the source count; `DESCRIBE` matches.

## Writing to S3/MinIO

```sql
COPY (SELECT * FROM read_csv('in.csv')) TO 's3://<bucket>/<project>/data/out.parquet'
     (FORMAT parquet, COMPRESSION zstd);
```

- Uses the same credentials as reads (`s3_onyxia_connection` or your session secret, see `s3-explore.md`).
- **Do not write under `diffusion/` unless the data is public**: that folder is readable by every Onyxia user.
- Keep the bucket/prefix in a parameter or environment variable, not in the code.
- Large inputs: stream straight from S3 to S3 in one `COPY`; do not download the source first.
