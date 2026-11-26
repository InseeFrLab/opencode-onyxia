---
name: duckdb-docs
description: Look up DuckDB syntax, functions, settings and extensions — first in the installed DuckDB's own catalog (offline, matches the platform version), then in the official docs/blog full-text index. Load on a DuckDB SQL error, when unsure of a function or option, or before guessing syntax. (keywords: doc duckdb, fonction duckdb, erreur SQL duckdb)
license: MIT
metadata:
  upstream: duckdb/duckdb-skills@44dfbbb
  adapted: onyxia
---

# DuckDB documentation lookup

Do not guess DuckDB syntax; look it up. Two tiers, cheapest first.

## 1. The installed DuckDB's own catalog (offline, exact for this version)

The CLI on Onyxia is older than the current docs (check `duckdb --version`; the docs describe DuckDB 2.0),
so confirm that a feature exists *here* before using it:

```sql
-- signature, description, examples of a function (many rows = overloads)
SELECT DISTINCT function_name, function_type, parameters, description, examples
FROM duckdb_functions() WHERE function_name ILIKE 'arg_max';
-- settings / extensions / keywords
SELECT name, description, value FROM duckdb_settings() WHERE name ILIKE '%memory%';
SELECT extension_name, installed, loaded, description FROM duckdb_extensions();
SELECT * FROM duckdb_keywords() WHERE keyword_name ILIKE 'qualify';
```

Error messages usually contain a hint (`Did you mean ...`, `Candidate functions`): read them first.

## 2. Official docs + blog search (BM25 full-text index)

```bash
uv run --no-project --with duckdb python -I scripts/search_docs.py "<keywords or function name>" \
    [--version 2.0|blog|all] [--limit 6] [--max-chars 1200] [--refresh]
```

(Path relative to this skill's directory.) It uses a recent DuckDB through `uv` because the hosted index
cannot be opened by the older preinstalled CLI. Prints the best chunks as `### section — page (version)`, URL,
text. Default `--version 2.0` = documentation; `blog` = background articles; `all` = both.

- **Search terms**: extract the technical nouns and function names (`"top n per group"` -> `arg_max max_by qualify`);
  a function name alone works best. Retry with fewer or different words if exit code is 3 (no match).
- **Cost**: ~6 KB of output for 6 chunks; lower `--limit` / `--max-chars` if you only need a signature.
- **Network**: needs outbound HTTPS to `duckdb.org` and PyPI (first run downloads the `duckdb` package and the
  index, cached 2 days in `~/.cache/duckdb-docs/`). Only your search keywords are involved; no project data
  is sent. Exit code 2 = index unavailable: say so and fall back to tier 1; do not retry in a loop.

## 3. Answering

1. Lead with the answer (a working snippet), then cite the doc URL.
2. If the docs describe a 2.0 feature that tier 1 does not list for the installed version, say so and give
   the older equivalent instead of a query that will fail.
3. Test the snippet on a small input before using it in a pipeline (`eda-duckdb/references/safe-query.md`).
