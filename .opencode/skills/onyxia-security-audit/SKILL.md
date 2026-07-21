# ONYXIA-SECURITY-AUDIT skill — proactive security & reproducibility checks

Run a lightweight security and reproducibility audit on a file or directory.
This skill is loaded automatically by the `reviewer` agent and is available
to the `build` agent before committing.

## What to check

### 1. Secret leakage 🔴
Scan for patterns that look like credentials:
- AWS keys (`AKIA[0-9A-Z]{16}`, `wJalrXUtnFEMI[...]`)
- Vault tokens (`hvs.[a-zA-Z0-9_-]{30,}`)
- Generic API keys / tokens (`api_key`, `apikey`, `token`, `secret`, `password`, `passwd`, `credential`)
- Private SSH keys (`-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----`)

**Only flag non-obvious/false positives** (e.g. variable *names* like `my_token` are info, not errors).
Flag values that are hard-coded strings: `password = "mysecretpass"`, `token: sk-abc...`.

### 2. Hardcoded S3 paths / buckets 🔴
Detect raw S3 URLs or bucket names baked into code:
- `s3://user-[^/]+/...` with a literal username instead of `$USERNAME` / `os.environ["USERNAME"]` / `Sys.getenv("USERNAME")`
- Hardcoded MinIO endpoint (`minio.lab.sspcloud.fr`) where `os.environ["AWS_S3_ENDPOINT"]` should be used
- Any absolute path pattern like `/local/path/to/data` that suggests a file was downloaded instead of streamed

### 3. Reproducibility gaps 🟡
- `.gitignore` missing: check project root — warn if absent or if it doesn't cover `.env`, `__pycache__`, `*.Rhistory`, `renv/`, `uv.lock`/`pyproject.toml`
- No `uv.lock` or `renv.lock` for Python / R projects
- Randomness without a fixed seed (`random.seed`, `set.seed`, `np.random.default_rng(seed)`)
- Parameterization: functions that accept file paths should use parameters, not variables named after a specific user/bucket

### 4. Data handling best practices 🟢
- Large CSV/JSON downloaded to disk → suggest `s3fs` / `arrow` / `duckdb` streaming
- No Parquet usage when dealing with >1k rows → suggest Parquet

## How to run

### Python files
```bash
# Secret scanning (basic regex)
grep -EniE '(AKIA[0-9A-Z]{14}|hvs\.|password\s*[:=]\s*"[^"]+"|secret\s*[:=]\s*"[^"]+"|api.key\s*[:=]\s*"[^"]+")' --include="*.py" .

# Hardcoded S3/MinIO
grep -EniE 'minio\.lab\.sspcloud\.fr|s3://(?!ENV_VAR)' --include="*.py" .

# Reproducibility
grep -EniE '(random\.(rand|choice|seed)|set\.seed|np\.random)' --include="*.py" .
```

### R files
```bash
grep -EniE '(password\s*<-?\s*"[^"]+"|secret\s*<-?\s*"[^"]+"|api.key\s*<-?\s*"[^"]+")' --include="*.R" .
grep -EniE 'minio\.lab\.sspcloud\.fr|s3://(?!ENV_VAR)' --include="*.R" .
grep -EniE 'set\.seed' --include="*.R" .
```

### Git history scan
```bash
# Check staged + recent history
git diff --cached --diff-filter=ACM | grep -EiE '(AKIA|hvs\.|password\s*[:=]\s*")'
git log -5 --oneline --diff-filter=ACM -- '*.py' '*.R' | xargs git diff --cached --diff-filter=ACM -G -E '(AKIA|hvs\.|password\s*[:=]\s*")' 2>/dev/null
```

## Output

Return a structured report:

```markdown
## Security & Reproducibility Audit
| # | file | line | category | severity | finding | recommendation |
|---|------|------|----------|----------|---------|----------------|
| 1 | src/train.py | 42 | secret | 🔴 error | Hardcoded password string "P@ssw0rd" | Move to Vault, use os.environ |
...
```

Classify:
- 🔴 **error** — blocks merge (secrets, hardcoded credentials)
- 🟡 **warning** — should fix (reproducibility gaps, missing lockfile)
- 🟢 **info** — nice-to-have (Parquet suggestion, seed recommendation)

## When this skill is loaded
- Automatically by `reviewer` subagent
- Automatically by `build` before any commit
- Manually: ask to "audit the repo for security and reproducibility"
