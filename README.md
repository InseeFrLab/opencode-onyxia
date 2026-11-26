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
├── onyxia-init.sh                 # Onyxia personal init script: installs opencode + a released config at service start
├── MANIFEST                       # runtime files shipped in the release tarball
├── INSTALL.md                     # detailed install guide
├── .github/workflows/release.yml  # checks on PRs; on a v* tag builds and publishes the release tarball
├── THIRD_PARTY.md  UPSTREAM.lock  # skills adapted from duckdb/duckdb-skills (MIT) and mlflow/skills (Apache-2.0)
├── licenses/                      # upstream licenses
├── scripts/vendor_mlflow_skills.py# re-creates the vendored mlflow-* skills from the pinned upstream revision
├── scripts/check_permissions.py   # model-free test of the permission rules (allow/ask/deny table)
├── scripts/check_install.py       # tests install.sh (full/--bare), the release tarball and onyxia-init.sh
├── scripts/build_dist.sh          # builds dist/opencode-onyxia.tar.gz (+ .sha256) from MANIFEST
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

**On SSP Cloud, the shortest route is the init script.** Under Onyxia → *My account* → *Services*, set the
initialization script and (optionally) its arguments:
```
URL   https://raw.githubusercontent.com/inseefrlab/opencode-onyxia/main/onyxia-init.sh
args  --version v1.0.0          # pin a release (default: latest); add --bare for the models only
```
Every new service then installs opencode v2 (if missing) and the released config, checksum-verified. The script
never makes the service fail: errors go to `~/.cache/opencode-onyxia-init.log`. The platform already injects
`OPENAI_BASE_URL` / `OPENAI_API_KEY`. If you already use another init script, add one line to it instead:
`curl -fsSL https://raw.githubusercontent.com/inseefrlab/opencode-onyxia/main/onyxia-init.sh | bash -s -- --version v1.0.0`.

Manual install from a clone:

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

   **Only want the models?** `./install.sh --bare` writes just the `onyxia` provider, its models and the default/title
   models: no agents, permissions, skills, commands or `AGENTS.md` (opencode then runs on its own defaults, so every
   tool is allowed without a prompt).
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
- v2 allows paths outside the project by default → `external_directory` asks again, except a short safe set (global skills, `/tmp`, caches);
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
- OpenCode is not sandboxed: `shell` commands really execute on the pod. Routine data science work
  runs **without prompts**; only a short list of dangerous actions asks, and catastrophic ones are blocked
  outright — see **Permissions** below.
- MCP disabled by default (a "remote" MCP would send context off-platform).
- Only the self-hosted gateway (`onyxia`) can be used as an LLM provider: a `provider.use` policy hides every other one
  (hosted OpenCode tier, OpenAI, Bedrock…) and a project cannot add its own, so prompts stay inside the SSP Cloud perimeter.
- On the public instance, only handle public / non-sensitive data.
- Never embed a token in a Git remote URL; use `gh auth login` or a credential
  helper (and `/check-secrets` before committing).

## Permissions: only dangerous things ask
`opencode.jsonc` has three layers (details and the full lists are commented in the file):

| Layer | What it does | Examples |
|---|---|---|
| **Baseline** `shell * allow` | Everything routine runs silently | `tail`, `rg`, `jq`, `mkdir`, `cp`, `uv`, `python`, `quarto`, `duckdb`, `aws s3 ls/cp`, `git add/commit`, `kubectl get`, plain `curl` downloads |
| **Ask** (`permissions`) | A human decides | `rm`, `git push` / `reset --hard` / `clean`, copying to **`diffusion/`** (public to all Onyxia users), `aws s3 mv/sync/presign`, `kubectl apply/exec`, `helm upgrade`, `argo submit`, `vault kv put`, uploads (`curl -d/-F/-T`, `ssh`/`scp`), `env`/`printenv`, dotenv files, paths outside the project (except skills, `/tmp`, caches), unknown websites |
| **Hard deny** (`policies`) | Blocked without a prompt | `sudo`, `rm -rf` of `/` or `~`, `curl … \| sh`, `eval`, **all remote deletes** (`aws s3 rm/rb`, `mc rm`, `kubectl delete`, `argo delete`, `helm uninstall`, `vault kv delete`), `nc`/`socat`, `~/.ssh` / `~/.gnupg` / `~/.netrc`, editing the global config, **any LLM provider other than `onyxia`** |

How to work with it:
- **Policies cannot be overridden** by a project's own `opencode.json`, nor by "Allow always" (the global config outranks
  project config). A project *can* relax an `ask` for itself, e.g. in its `opencode.json`:
  `"permissions": [{ "action": "shell", "resource": "kubectl scale *", "effect": "allow" }]`.
- **Rules match the raw text of each subcommand, and the last matching rule wins.** The shell scanner splits
  pipelines, `&&`/`;`, subshells, `if …; then` and `$(…)`, but it does not look inside a quoted string and does not
  unwrap commands: **`env sudo x`, `timeout 5 sudo x`, `nohup …`, `/usr/bin/sudo x`, `xargs sudo` and
  `bash -c "sudo x"` all slip past a plain `sudo *` pattern** (verified in a live session). So dangerous phrases are
  substring patterns (`*aws s3 rm*`), single words also match after a space, a slash or a quote, and
  `bash -c "…"` / `sh -c "…"` **ask** so a human reads the string. Consequences: a standalone word such as `sudo `
  is blocked even inside a commit message (a known false positive), and `python -c`, scripts, aliases or
  obfuscation (`r''m`) still get through. Write every new rule in both option forms
  (`aws s3 rm*` and `aws -* s3 rm*`: `--endpoint-url` before the subcommand is the documented form here).
- **Do not use `opencode --auto`** with this config: it auto-approves every `ask` (`git push`, publishing to
  `diffusion/`…); denies and policies still hold.
- "Allow always" saves project-scoped approvals (lost with an ephemeral service); audit them with
  `opencode api GET /api/permission/saved`.
- This is a guard-rail, not a sandbox: patterns cannot see through `/bin/rm`, variables or code (`python script.py`,
  SQL `COPY … TO 's3://…'`). Platform admins can ship the same `policies` in `/etc/opencode/opencode.json` (highest
  authority, not editable by users).
- **Test the rules** after any change (no model needed, ~1 min):
  `python3 -I scripts/check_permissions.py` (`--ref HEAD~1` replays the table on an older config).

## Overriding the config for one project
The config is installed **globally** (`~/.config/opencode`); a project overrides only what differs, committed with
the project — nothing to copy. Everything below follows the official docs
([Config](https://opencode.ai/docs/config/), [Agents](https://opencode.ai/docs/agents/),
[Skills](https://opencode.ai/docs/skills/), [Commands](https://opencode.ai/docs/commands/),
[Instructions](https://opencode.ai/docs/instructions/), [Permissions](https://opencode.ai/docs/permissions/),
[Policies](https://opencode.ai/docs/policies/), [MCP servers](https://opencode.ai/docs/mcp-servers/)) and was tested
against opencode 2.1.2.

```
my-project/
├── AGENTS.md                  # extra instructions, added to the global Onyxia AGENTS.md
├── opencode.jsonc             # project settings (or .opencode/opencode.jsonc — use ONE of the two forms)
└── .opencode/
    ├── skills/<id>/SKILL.md   # project skills
    ├── commands/<name>.md     # project slash commands
    └── agents/<name>.md       # project agents
```
Write overrides in the native v2 shape (`permissions`, `agents`, `commands`, `providers`, `mcp.servers`; actions
`shell` / `subagent`, not `bash` / `task`) and do not mix v1 and v2 syntax inside one nested entry.

**Precedence**, lowest to highest: ① `~/.config/opencode/opencode.jsonc` (this repo, installed by `install.sh`) →
② project `opencode.json(c)` (parent directories first, the nearest last) → ③ `.opencode/opencode.json(c)`
(beats every direct `opencode.json(c)`) → ④ `/etc/opencode/opencode.json` (managed: users and projects cannot override
it). Settings that do not conflict are kept. `policies` are evaluated in the **reverse** order, so a project can never
lift this repo's hard denies. `update` is read from the global config only.

| What | How a project combines with the global config |
|---|---|
| scalars (`model`, `default_agent`, `steps`…) | the nearest wins |
| `permissions` | project rules are appended after the global ones, last match wins (but see the agent gotcha below) |
| `agents.<id>` | merged by id: scalars replace, `permissions` append, `disabled: true` removes it, a new id adds one |
| `providers.<id>.models` | merged: your model is added next to the shipped ones |
| `skills`, `instructions` | the lists are combined |
| a skill with the same ID, a command with the same name | the project one **replaces** the global one |
| `mcp.servers.<name>` | the **whole object is replaced**: repeat `type`, `url`/`command`… |
| `AGENTS.md` files | all are combined; conflicts are not resolved |

### Model and agents
```jsonc
// opencode.jsonc
{
  "agents": {
    "build": { "model": "onyxia/qwen3-8-27b#think" },   // thinking mode for this project (variants: see above)
    "python-ds": { "steps": 25 },                       // the shipped prompt, permissions and model are kept
    "reviewer": { "disabled": true }                    // remove a shipped agent
  },
  "providers": { "onyxia": { "models": {                // add a model served by the gateway, then select it
    "qwen3-6-35b-moe": { "name": "Qwen3.6 35B MoE", "capabilities": { "tools": true },
                         "limit": { "context": 131072, "output": 16384 } }
  } } }
}
```
A new agent is a Markdown file, e.g. `.opencode/agents/data-cleaner.md`: the frontmatter is an `agents` entry and the
body is its system prompt (a custom agent starts from your prompt only; the shipped ones start from
`prompts/shared/base.md`).
```markdown
---
description: Cleans raw survey extracts with duckdb
mode: subagent
steps: 20
permissions:
  - action: edit
    resource: "data/*"
    effect: deny
---
You clean raw extracts into tidy Parquet. Never edit files under data/.
```

### Permissions
```jsonc
{
  "permissions": [
    { "action": "shell", "resource": "kubectl scale *", "effect": "allow" },   // relax an ask for this project
    { "action": "shell", "resource": "git commit*", "effect": "ask" }          // or tighten something
  ],
  "agents": {
    // build, python-ds, r-ds and mlops ship their own `edit * allow`; it is appended AFTER the project rules,
    // so restrict edits inside the agents (repeat for r-ds and mlops if you use them):
    "build":     { "permissions": [{ "action": "edit", "resource": "src/legacy/*", "effect": "ask" }] },
    "python-ds": { "permissions": [{ "action": "edit", "resource": "src/legacy/*", "effect": "ask" }] }
  }
}
```
- **Agent rules are appended after project rules.** A top-level project `edit … ask` is overridden by those agents'
  `edit * allow` (tested), and a top-level `shell … allow` works for `build` but not for `plan` (its `shell * ask`)
  or `reviewer` (its deny list): put the rule under `agents.<id>.permissions` for those.
- A project can relax an `ask`, but **not** a hard deny: `sudo`, `kubectl delete`… stay blocked whatever the
  project says (see **Permissions** above for the model, both option forms and `--auto`).
- To hide a shipped skill from the model: `{ "action": "skill", "resource": "mlflow-*", "effect": "deny" }`.

### Skills, commands, instructions
- **Skills**: `.opencode/skills/<id>/SKILL.md` adds a skill (ID = directory name; `name` and `description` in the
  frontmatter; `references/`, `scripts/` next to it). Reusing a shipped ID — copy the whole directory — replaces
  that skill for the project. `"skills": ["./team-skills"]` adds extra folders (relative to the working directory).
- **Commands**: `.opencode/commands/etl.md` becomes `/etl`; the same name as a shipped command (`/verify`,
  `/new-project`, `/diagnose`, `/check-secrets`) replaces it.
  ```markdown
  ---
  description: Run the survey ETL
  agent: build
  ---
  Run the ETL for $ARGUMENTS and report row counts.
  ```
- **Instructions**: a project `AGENTS.md` is loaded after the global Onyxia one (it adds to it, it cannot remove
  it): put the bucket/prefix convention, dataset names, `uv`/`renv`/Quarto conventions, "never touch `data/raw`".
  `"instructions": ["docs/guidelines/*.md"]` adds files, globs or URLs; `"references"` makes a sibling folder or a Git
  repository available as named context (both per the official docs).

### MCP and secrets
```jsonc
// enable the data.gouv.fr MCP server for this project only (the whole object is replaced: repeat type + url)
{ "mcp": { "servers": { "datagouv": { "type": "remote", "url": "https://mcp.data.gouv.fr/mcp", "disabled": false } } } }
```
`opencode mcp add <name> …` writes the project config (`--global` for every project). A remote MCP sends context off
the platform: public data only. Keep secrets out of the repository: `{env:NAME}` / `{file:~/.secrets/key}` in the
config, with the value injected by Vault as an environment variable.

### Limits, trust, and checking what applies
- A repository's `opencode.jsonc` and `.opencode/` are **code**: they can add MCP servers, commands and agents, so
  review them before running opencode in a clone you do not trust. They **cannot** redirect LLM traffic: a
  `provider.use` policy allows only `onyxia`, so a provider added by a project is unusable (an agent pointing at it
  falls back to the default model, an explicit `-m` fails with "Model unavailable"). MCP servers are not covered —
  the `mcp.use` policy needs a newer opencode than the 2.1.2 pinned on the platform.
  To allow another provider on purpose, add a `provider.use` allow to the global `policies`.
  `OPENCODE_DISABLE_PROJECT_CONFIG=1` makes opencode ignore project config and project skills (for the background
  service: `opencode service set env OPENCODE_DISABLE_PROJECT_CONFIG 1 && opencode service restart`). Platform admins
  can enforce rules users cannot change with `policies` in `/etc/opencode/opencode.json`.
- `opencode debug config` lists the config sources in load order, `opencode debug agents` the resolved agents (model,
  steps, permissions), `opencode mcp list` the MCP servers. The background service caches the config: if an edit does
  not show up, run `opencode reload`.
- `python3 -I scripts/check_permissions.py` tests the permission model (its sandbox includes a project config that
  relaxes one ask and tries to lift two hard denies).

## Customization
These steps change the shipped config for everyone; to change a single project only, see
**Overriding the config for one project** above.
- Add an agent: new block under `agents` (`system` = `{file:./prompts/<name>.md}`) + a prompt in `prompts/`.
- Add know-how: new folder `.opencode/skills/<name>/SKILL.md`
  (YAML header with `name` + `description` required). Larger skills can bundle
  `references/` (loaded on demand), `scripts/` (executable helpers) and
  `assets/` (copyable templates).
- Add a command: new file `.opencode/commands/<name>.md`.
- The skills follow the Agent Skills standard: skills written for Claude Code
  work as-is, and `./install.sh --claude` exposes these ones to Claude Code.
