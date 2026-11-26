#!/usr/bin/env python3
"""Search the official DuckDB documentation + blog (BM25 full-text index), with a local cache.

Run it through uv so a recent DuckDB is used (the hosted index is built with a DuckDB newer than the
CLI preinstalled on Onyxia, which cannot open it):

    uv run --no-project --with duckdb python -I scripts/search_docs.py "window functions" [--version 2.0|blog|all]
                                                                       [--limit 6] [--max-chars 1200] [--refresh]

Only the search keywords stay local; the script downloads the public index (cached 2 days) and nothing else.
Adapted from the `duckdb-docs` skill of duckdb/duckdb-skills (MIT), see THIRD_PARTY.md.

Exit codes: 0 results printed, 3 no match, 2 index unavailable (network/DuckDB error).
Env: DUCKDB_DOCS_INDEX_URL, DUCKDB_DOCS_CACHE override the index URL and the cache file.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

import duckdb

URL = os.environ.get("DUCKDB_DOCS_INDEX_URL", "https://duckdb.org/data/docs-search.duckdb")
CACHE = Path(os.environ.get("DUCKDB_DOCS_CACHE", Path.home() / ".cache" / "duckdb-docs" / "docs-search.duckdb"))
MAX_AGE_SECONDS = 2 * 24 * 3600
SITE = "https://duckdb.org"


def refresh() -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE.with_name(CACHE.name + ".tmp")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs; INSTALL fts; LOAD httpfs; LOAD fts;")
        con.execute(f"ATTACH '{URL}' AS remote (READ_ONLY)")
        con.execute(f"ATTACH '{tmp}' AS tmp")
        con.execute("COPY FROM DATABASE remote TO tmp")
    finally:
        con.close()
    tmp.replace(CACHE)


def ensure_cache(force: bool) -> None:
    fresh = CACHE.exists() and (time.time() - CACHE.stat().st_mtime) < MAX_AGE_SECONDS
    if force or not fresh:
        try:
            refresh()
        except Exception as exc:  # noqa: BLE001 - network, egress, storage-version errors all degrade the same way
            if CACHE.exists():
                print(f"[warn] could not refresh the index ({str(exc)[:150]}); using the stale cache", file=sys.stderr)
            else:
                print(f"[error] docs index unavailable: {str(exc)[:300]}", file=sys.stderr)
                sys.exit(2)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("query", help="keywords or a function name, e.g. 'arg_max' or 'read csv delimiter'")
    ap.add_argument("--version", default="2.0", help="'2.0' (docs, default), 'blog' or 'all'")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--max-chars", type=int, default=1200, help="truncate each chunk (keeps the output small)")
    ap.add_argument("--refresh", action="store_true", help="force re-download of the index")
    args = ap.parse_args()

    terms = " ".join(re.findall(r"\w+", args.query))
    if not terms:
        print("[error] empty query", file=sys.stderr)
        sys.exit(2)

    ensure_cache(args.refresh)
    con = duckdb.connect(str(CACHE), read_only=True)
    con.execute("LOAD fts")
    where = "score IS NOT NULL" + ("" if args.version == "all" else " AND version = ?")
    params = [terms] + ([] if args.version == "all" else [args.version]) + [args.limit]
    # DuckDB 2.x cannot reference the BM25 alias in WHERE of the same SELECT: compute it in a subquery.
    rows = con.execute(
        f"""SELECT page_title, section, url, version, text, score
            FROM (SELECT *, fts_main_docs_chunks.match_bm25(chunk_id, ?) AS score FROM docs_chunks)
            WHERE {where} ORDER BY score DESC LIMIT ?""",
        params,
    ).fetchall()
    if not rows:
        print(f"No match for {terms!r} in version {args.version!r}. Try fewer or different keywords, or --version all.")
        sys.exit(3)
    for title, section, url, version, text, _score in rows:
        link = url if str(url).startswith("http") else SITE + str(url)
        body = (text or "").strip()
        if len(body) > args.max_chars:
            body = body[: args.max_chars].rstrip() + " [...]"
        print(f"### {section or title} — {title} ({version})\n{link}\n\n{body}\n\n---")


if __name__ == "__main__":
    main()
