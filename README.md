# Multi-agent OpenCode configuration for Onyxia (Insee)

Ready-to-use configuration to drive **R and Python data science / MLOps
projects** from OpenCode in the **Onyxia / SSP Cloud** environment, backed by
the platform's **self-hosted models** (data sent to the agents therefore stays
within the Insee perimeter).

## Contents
```
opencode-onyxia/
├── opencode.jsonc                 # main config (native opencode v2): providers, models/variants, agents, permissions, MCP
├── AGENTS.md                      # Onyxia context shared by ALL agents (loaded automatically)
├── install.sh                     # GLOBAL install into ~/.config/opencode (all projects)
├── INSTALL.md                     # detailed install guide
├── THIRD_PARTY.md  UPSTREAM.lock  # skills adapted from duckdb/duckdb-skills (MIT) and mlflow/skills (Apache-2.0)
├── licenses/                      # upstream licenses
├── scripts/vendor_mlflow_skills.py# re-creates the vendored mlflow-* skills from the pinned upstream revision
├── prompts/                       # one system prompt per agent
│   ├── build.md  plan.md  python-ds.md  r-ds.md  mlops.md  reviewer.md  dataviz-vision.md
└── .opencode/
    ├── commands/                  # slash commands (/new-project, /check-secrets, /diagnose)
    └── skills/                    # know-how loaded on demand (1 folder = 1 skill)
        ├── onyxia-storage-s3/     # S3/MinIO access (+ references/, scripts/check_s3.sh)
        ├── eda-duckdb/            # exploratory analysis over S3 (+ scripts/profile_parquet.py,
        │                          #   references/: friendly SQL, safe/bounded queries, S3 explore, convert)
        ├── duckdb-docs/           # DuckDB syntax lookup: local catalog + official docs search (scripts/search_docs.py)
        ├── data-validation/       # data quality checks (pandera, pointblank, duckdb)
        ├── insee-public-data/     # French public data (Insee, data.gouv.fr, COG)
        ├── mlflow-tracking/       # experiment tracking, run comparison, registry (classic ML)
        ├── mlflow-docs/ mlflow-trace-instrumentation/ mlflow-trace-retrieval/
        │   mlflow-trace-analysis/ mlflow-evaluation/   # LLM-app tracing & evaluation (adapted from mlflow/skills)
        ├── argo-mlops/            # industrialization (+ references/, assets/workflow-template.yaml)
        ├── onyxia-diagnostics/    # runbook: red service, 403, OOM, failed workflow
        ├── python-datascience/    # Python standards (uv, ruff, pytest, polars…)
        ├── r-datascience/         # R standards (renv, targets, testthat, utilitR)
        ├── onyxia-reproducibility/# the four pillars of reproducibility
        ├── quarto-publication/    # reports & publishing (+ references/, assets/)
        ├── vault-secrets-onyxia/  # secrets via Vault
        └── git-workflow-ds/       # DS Git workflow (+ scripts/setup-nbstripout.sh)
```

## Installation (summary — detailed guide in `INSTALL.md`)
1. **Install OpenCode v2** in the service (VSCode/Jupyter). This config is in the
   *native v2 format* and cannot be read by OpenCode v1:
   ```bash
   curl -fsSL https://opencode.ai/v2/install | bash
   opencode --version      # must print v2.x
   ```
2. **Install the config globally** (applies to all projects) — script provided:
   ```bash
   cd opencode-onyxia && ./install.sh          # add --claude to also serve Claude Code
   ```
   It copies the config, `AGENTS.md`, prompts, skills and commands into
   `~/.config/opencode/`. Details and alternatives (manual, Git-tracked,
   per-project overrides) in **`INSTALL.md`**.
3. **Get an API key** from the Open WebUI gateway
   `https://llm.lab.sspcloud.fr` (Settings → Account → API Keys), then set the
   two environment variables:
   ```bash
   export OPENAI_BASE_URL="https://llm.lab.sspcloud.fr/api"
   export OPENAI_API_KEY="sk-……"
   ```
   (Ideally stored in Vault and injected by the service.)
4. **Check the endpoint**:
   ```bash
   curl -s "$OPENAI_BASE_URL/chat/completions" \
     -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
     -d '{"model":"qwen3-8-27b","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
   ```
   The model ids (`qwen3-8-27b`, `gemma4-26b-moe`, `qwen3-vl`) are
   confirmed and already present in the config.
5. **Launch**: `opencode` then `/models` to confirm the models are listed.

## Usage
- **Switch between primary agents** (`build` ⇄ `plan`): **Tab** key.
- **Delegate**: subagents (`python-ds`, `r-ds`, `mlops`, `reviewer`,
  `dataviz-vision`) are invoked automatically as needed, or explicitly via
  `@name` (e.g. `@reviewer review the diff`, `@mlops deploy this model`).
- **Skills**: loaded automatically when the task matches their description;
  you can also reference them in a prompt.
- **Commands**:
  - `/new-project` — scaffold a reproducible R/Python project (uv or renv,
    tests, `.gitignore`, nbstripout, parameterized S3 paths, Quarto stub);
  - `/check-secrets` — scan the repo (tree, staged, remotes, recent history)
    for leaked credentials before committing;
  - `/diagnose` — run the Onyxia runbook when a service or job misbehaves.

## Model allocation
| Model | Role in the config |
|---|---|
| `qwen3-8-27b` | default model — agent `plan` (variant `#plan`, **thinking mode on**) and agents `build`/`python-ds`/`r-ds`/`mlops` (variant `#build`, thinking off, faster) |
| `gemma4-26b-moe` | session titles (`agents.title`) + agent `reviewer` (variant `#review`, diverse point of view) |
| `qwen3-vl` | agent `dataviz-vision` (variant `#vision`) — reading charts, diagrams, screenshots |

### Sampling and thinking mode (model variants)
The gateway serves `qwen3-8-27b` with thinking **on** by default. The config does not rely
on that: `chat_template_kwargs.enable_thinking` is pinned to `false` on the model entry, and the
`plan` agent turns it back on.

> **OpenCode v2 change:** an agent's `request.body` (v1: `temperature`, `top_p`, `options`) is
> accepted but **never sent to the model**. Sampling and provider options therefore live in
> model **variants** (`providers.onyxia.models.<model>.variants`), and an agent selects one with
> `provider/model#variant`, e.g. `"model": "onyxia/qwen3-8-27b#plan"`.

To get a reasoning trace on another agent, point it at the `#plan` variant, or pick the `#think` variant of
`onyxia/qwen3-8-27b` for a session (same settings, usable on any agent): thinking on with the sampling Qwen
recommends for it — `temperature` 0.6, `top_p` 0.95, `top_k` 20, `min_p` 0 (Qwen3 loops on repetitions when it
reasons under near-greedy decoding). Or add your own variant:
```jsonc
"variants": [
  { "id": "deep", "body": { "temperature": 0.6, "top_p": 0.95,
                            "chat_template_kwargs": { "enable_thinking": true } } }
]
```

## Migrated from OpenCode v1
`opencode.jsonc` is now **native v2** (`providers`, `agents`, ordered `permissions[]`,
`mcp.servers`, `update`, `commands/`). v1 and v2 share the same config locations, so v1 can no
longer read these files. Things that behave differently from the v1 version of this repo:
- sampling/thinking → model variants (see above);
- `compaction.prune` / `tail_turns` no longer exist → `compaction.keep.tokens`;
- `experimental.continue_loop_on_deny` is ignored by v2;
- v2 allows paths outside the project by default → an `external_directory: ask` rule restores v1's behaviour;
- permission actions renamed: `bash` → `shell`, `task` → `subagent`.

Official guide: <https://opencode.ai/docs/migrate-v1/>.

## Third-party skills
Some skills are adapted from official upstream projects — **DuckDB** ([duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills),
MIT) and **MLflow** ([mlflow/skills](https://github.com/mlflow/skills), Apache-2.0) — and corrected for Onyxia
(MinIO credentials, DuckDB 1.5 vs 2.0, models kept on the platform gateway). `THIRD_PARTY.md` lists what was taken,
what changed and the pinned revisions. The MLflow GenAI skills (`mlflow-trace-*`, `mlflow-evaluation`) need an
**MLflow >= 3 server**: they check `MLFLOW_TRACKING_URI`'s version first and stop if it is older or unreachable.

## Bundled MCP servers (disabled by default)
Two `remote` servers are pre-declared in `opencode.jsonc` with
`"disabled": true`: **excalidraw** (diagrams, requires `EXCALIDRAW_API_KEY`)
and **datagouv** (public data from data.gouv.fr). Activation and
confidentiality precautions: see `INSTALL.md`.

## Security / confidentiality
- OpenCode is not sandboxed: `shell` commands really execute on the pod.
  The permissions in `opencode.jsonc` allow the usual data science tooling and
  **ask for confirmation** for network, Kubernetes mutations, and deletions.
- MCP disabled by default (a "remote" MCP would send context off-platform).
- On the public instance, only handle public / non-sensitive data.
- Never embed a token in a Git remote URL; use `gh auth login` or a credential
  helper (and `/check-secrets` before committing).

## Customization
- Add an agent: new block under `agents` (`system` = `{file:./prompts/<name>.md}`) + a prompt in `prompts/`.
- Add know-how: new folder `.opencode/skills/<name>/SKILL.md`
  (YAML header with `name` + `description` required). Larger skills can bundle
  `references/` (loaded on demand), `scripts/` (executable helpers) and
  `assets/` (copyable templates).
- Add a command: new file `.opencode/commands/<name>.md`.
- The skills follow the Agent Skills standard: skills written for Claude Code
  work as-is, and `./install.sh --claude` exposes these ones to Claude Code.
