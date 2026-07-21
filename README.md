# Multi-agent OpenCode configuration for Onyxia (Insee)

Ready-to-use configuration to drive **R and Python data science / MLOps
projects** from OpenCode in the **Onyxia / SSP Cloud** environment, backed by
the platform's **self-hosted models** (data sent to the agents therefore stays
within the Insee perimeter).

## Contents
```
opencode-onyxia/
├── opencode.jsonc                 # main config: provider, models, agents, permissions, MCP
├── AGENTS.md                      # Onyxia context shared by ALL agents (loaded automatically)
├── install.sh                     # GLOBAL install into ~/.config/opencode (all projects)
├── INSTALL.md                     # detailed install guide
├── prompts/                       # one system prompt per agent
│   ├── build.md  plan.md  python-ds.md  r-ds.md  mlops.md  reviewer.md  dataviz-vision.md
└── .opencode/
    ├── command/                   # slash commands (/new-project, /check-secrets, /diagnose)
    └── skills/                    # know-how loaded on demand (1 folder = 1 skill)
        ├── onyxia-storage-s3/     # S3/MinIO access (+ references/, scripts/check_s3.sh)
        ├── eda-duckdb/            # exploratory analysis over S3 (+ scripts/profile_parquet.py)
        ├── data-validation/       # data quality checks (pandera, pointblank, duckdb)
        ├── insee-public-data/     # French public data (Insee, data.gouv.fr, COG)
        ├── mlflow-tracking/       # experiment tracking, run comparison, registry
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
1. **Install OpenCode** in the service (VSCode/Jupyter):
   ```bash
   curl -fsSL https://opencode.ai/install | bash
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
   export OPENAI_BASE_URL="https://llm.lab.sspcloud.fr/v1"
   export OPENAI_API_KEY="sk-……"
   ```
   (Ideally stored in Vault and injected by the service.)
4. **Check the endpoint** (Open WebUI exposes `/v1` *and* `/api`):
   ```bash
   curl -s "$OPENAI_BASE_URL/chat/completions" \
     -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
     -d '{"model":"qwen3-6-35b-moe","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
   ```
   A `chat.completion` response → `/v1` is correct; `404` → use `…/api`.
   The model ids (`qwen3-6-35b-moe`, `gemma4-26b-moe`, `qwen3-vl`) are
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
| `qwen3-6-35b-moe` | default model — code, reasoning, agents `build`/`plan`/`python-ds`/`r-ds`/`mlops` |
| `gemma4-26b-moe` | `small_model` (titles, summaries) + agent `reviewer` (diverse point of view) |
| `qwen3-vl` | agent `dataviz-vision` — reading charts, diagrams, screenshots |

## Bundled MCP servers (disabled by default)
Two `remote` servers are pre-declared in `opencode.jsonc` with
`"enabled": false`: **excalidraw** (diagrams, requires `EXCALIDRAW_API_KEY`)
and **datagouv** (public data from data.gouv.fr). Activation and
confidentiality precautions: see `INSTALL.md`.

## Security / confidentiality
- OpenCode is not sandboxed: `bash` commands really execute on the pod.
  The permissions in `opencode.jsonc` allow the usual data science tooling and
  **ask for confirmation** for network, Kubernetes mutations, and deletions.
- MCP disabled by default (a "remote" MCP would send context off-platform).
- On the public instance, only handle public / non-sensitive data.
- Never embed a token in a Git remote URL; use `gh auth login` or a credential
  helper (and `/check-secrets` before committing).

## Customization
- Add an agent: new block under `agent` + a prompt in `prompts/`.
- Add know-how: new folder `.opencode/skills/<name>/SKILL.md`
  (YAML header with `name` + `description` required). Larger skills can bundle
  `references/` (loaded on demand), `scripts/` (executable helpers) and
  `assets/` (copyable templates).
- Add a command: new file `.opencode/command/<name>.md`.
- The skills follow the Agent Skills standard: skills written for Claude Code
  work as-is, and `./install.sh --claude` exposes these ones to Claude Code.
