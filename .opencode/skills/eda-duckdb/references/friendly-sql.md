# DuckDB "Friendly SQL" cheat sheet

> Adapted from the `query` skill of [duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills)
> (MIT) — see `THIRD_PARTY.md`. Examples assume a table/file `t(id, grp, v, d)`.

Prefer these idioms: shorter, fewer places to make a mistake, and what DuckDB users expect to read.

## Compact clauses
- **FROM-first**: `FROM t WHERE v > 10` (implicit `SELECT *`).
- **`GROUP BY ALL`** / **`ORDER BY ALL`**: group by every non-aggregate column / sort by all columns
  (deterministic output): `SELECT grp, count() FROM t GROUP BY ALL ORDER BY ALL`.
- **`SELECT * EXCLUDE (a, b)`**, **`SELECT * REPLACE (v * 2 AS v)`**.
- **`UNION ALL BY NAME`**: stack tables whose columns are in a different order.
- **`LIMIT 10%`**: percentage limit. Trailing commas are allowed in `SELECT` lists.
- **`count()`** instead of `count(*)`.
- **Column aliases are reusable**: in `WHERE`, `GROUP BY`, `HAVING` and later select items
  (`SELECT v * 2 AS w, w + 1 AS x`).

## Aggregation and windows
- **`FILTER`**: `count() FILTER (WHERE v > 10)` for conditional aggregates.
- **Top-N per group without a subquery**: `max(v, 3)` (list of the 3 largest), `arg_max(id, v, 3)`,
  `min_by(id, v, 3)`.
- **`QUALIFY`** filters on window results: keep the latest row per key
  `FROM t QUALIFY row_number() OVER (PARTITION BY id ORDER BY d DESC) = 1`.
- **`COLUMNS(*)`** applies an expression to many columns (regex, `EXCLUDE`, lambdas):
  `SELECT min(COLUMNS(*)) FROM t`, `SELECT COLUMNS('^v_') FROM t`.
- **`GROUPING SETS` / `CUBE` / `ROLLUP`** for multi-level totals.
- **`PIVOT` / `UNPIVOT`** to reshape wide <-> long: `PIVOT t ON grp USING sum(v) GROUP BY d`.
- **`DESCRIBE t`** (schema) and **`SUMMARIZE t`** (full statistical profile in one scan).

## Joins
- **`ASOF JOIN`**: match each row to the closest earlier/later one (prices at a timestamp, event logs).
- **`POSITIONAL JOIN`**: match rows by position; **`LATERAL`** to reference previous tables in a subquery.
- Always join on explicit keys; check the key is unique first
  (`SELECT count() - count(DISTINCT id) FROM t`) to avoid silent row multiplication.

## Reading data
- **Query a file directly**: `FROM 'data.parquet'`, `FROM 'data.csv'`, `FROM 'part-*.parquet'` (glob).
- **Hive-partitioned folders**: `FROM read_parquet('s3://<bucket>/ds/*/*.parquet', hive_partitioning = true)`.
- CSV types are auto-detected; for robust inference use `read_csv(..., sample_size = -1)`.

## Expressions and types
- **Dot chaining**: `grp.trim().lower()` on a column, or `('  Hello ').trim().lower()` (a bare string literal
  needs parentheses); **slicing**: `s[1:3]`, `lst[-1]`; **lists**: `[1, 2, 3]`.
- **List comprehension**: `[x * 2 FOR x IN lst]`; **`format('{}-{}', a, b)`**; `STRUCT.*`: `SELECT s.* FROM ...`.
- **SQL variables**: `SET VARIABLE n = 100; SELECT * FROM t LIMIT getvariable('n')`.

## Writing and modifying
- `CREATE OR REPLACE TABLE x AS SELECT ...` (no `DROP IF EXISTS`), `INSERT INTO x BY NAME SELECT ...`,
  `INSERT OR REPLACE INTO` / `INSERT OR IGNORE INTO` for upserts.
- Export with `COPY (...) TO 'out.parquet' (FORMAT parquet, COMPRESSION zstd)` (see `convert.md`).

## Look things up locally before guessing
Function signatures and settings are in DuckDB's own catalog, offline and always matching the installed version:
`FROM duckdb_functions() WHERE function_name = 'arg_max'` (columns `parameters`, `description`, `examples`),
`FROM duckdb_settings() WHERE name ILIKE '%memory%'`. For anything else, use the `duckdb-docs` skill.
