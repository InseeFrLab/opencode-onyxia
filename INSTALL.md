# INSTALL — GLOBAL OpenCode configuration (applies to all projects)

This configuration installs **globally** into `~/.config/opencode/`.
It then applies to **all your projects**, on any interactive service
(VSCode-python, Jupyter, RStudio) launched on the SSP Cloud — without copying
it into each repository.

Target tree once installed:

```txt
~/.config/opencode/
├── opencode.jsonc      # native v2 config: providers, agents, permissions
├── AGENTS.md           # Onyxia context applied to ALL sessions
├── prompts/*.md        # agent system prompts
├── commands/*.md       # slash commands (/new-project, /check-secrets, /diagnose)
└── skills/<name>/      # global skills (NB: without the .opencode prefix)
    ├── SKILL.md        #   instructions loaded on demand
    ├── references/     #   optional: detailed recipes, loaded only when needed
    ├── scripts/        #   optional: executable helpers (diagnostics, setup)
    └── assets/         #   optional: copyable templates
```

---

## 1. Install OpenCode v2

This configuration uses the **native OpenCode v2 format** (it cannot be read by v1).
Remove any v1 install first — v1 and v2 both provide the `opencode` command.

```bash
curl -fsSL https://opencode.ai/v2/install | bash
opencode --version      # must print v2.x
```

## 2. Get an Open WebUI API key

In `https://llm.lab.sspcloud.fr`: profile menu -> **Settings** -> **Account** ->
**API Keys** -> generate/show a key (format `sk-...`).

## 3. Set the two environment variables (once and for all)

Put them in `~/.bashrc` so they apply to every service:

```bash
echo 'export OPENAI_BASE_URL="https://llm.lab.sspcloud.fr/api"' >> ~/.bashrc
echo 'export OPENAI_API_KEY="sk-……"' >> ~/.bashrc
source ~/.bashrc
```

> Recommended: store the key in **Vault** (Onyxia's "Mes secrets" tab) and
> inject it as an environment variable when creating services — the key then
> never appears in plain text.

## 4. Install the config globally

### Method A — provided script (recommended)

From the unpacked repository folder:

```bash
cd opencode-onyxia
./install.sh
```

The script copies `opencode.jsonc`, `AGENTS.md`, `prompts/` and `commands/`
into `~/.config/opencode/`, and the skills into `~/.config/opencode/skills/`
(it backs up an existing config first — moving a legacy v1 `command/` directory into the
backup — and keeps bundled skill scripts executable).

Optional — also expose the skills to **Claude Code**:

```bash
./install.sh --claude      # additionally copies the skills to ~/.claude/skills/
```

### Method B — manual

```bash
cd opencode-onyxia
mkdir -p ~/.config/opencode/prompts ~/.config/opencode/skills ~/.config/opencode/commands
cp  opencode.jsonc AGENTS.md  ~/.config/opencode/
cp -r prompts/.               ~/.config/opencode/prompts/
cp -r .opencode/skills/.      ~/.config/opencode/skills/
cp -r .opencode/commands/.    ~/.config/opencode/commands/
```

### Method C — track the repository with Git (easy updates via `git pull`)

```bash
git clone https://github.com/InseeFrLab/opencode-onyxia ~/opencode-onyxia
cd ~/opencode-onyxia && ./install.sh
# to update later:  cd ~/opencode-onyxia && git pull && ./install.sh
```

> Do not clone directly *into* `~/.config/opencode`: global skills must live
> in `~/.config/opencode/skills/` (without the `.opencode/` prefix a *project*
> config uses). The script handles this detail.

> **Git authentication**: use `gh auth login` or a credential helper. Never
> put a token in the remote URL (`https://ghp_…@github.com/…`) — it ends up
> in plain text in `.git/config`, survives in every clone, and is exactly the
> kind of leak the `/check-secrets` command hunts for.

## 5. Use it, from any project

```bash
cd ~/work/any-project
opencode
```

- `/models` -> `qwen3-8-27b`, `gemma4-26b-moe`, `qwen3-vl` under
  "SSPCloud LLM (self-hosted)".
- **Tab** -> switch `build` <-> `plan`.
- `@python-ds`, `@r-ds`, `@mlops`, `@reviewer`, `@dataviz-vision` -> subagents
  (also delegated automatically). Skills load based on context.
- `/new-project`, `/check-secrets`, `/diagnose` -> bundled commands.

The global config applies everywhere; no per-project installation is needed.

---

## Overriding locally in a project (optional)

A project adds to or overrides the global config with its own `opencode.jsonc`, `AGENTS.md` and
`.opencode/{skills,commands,agents}/` — precedence, merge rules, recipes (model, permissions, agents, skills,
commands, instructions, MCP) and caveats are in the README section
**"Overriding the config for one project"**.

## MCP servers (optional, disabled by default)

`opencode.jsonc` pre-declares two `remote` MCP servers with `"disabled": true`:

- **excalidraw** (`https://api.excalidraw.com/api/v1/mcp`): diagram creation.
  Requires a key in `EXCALIDRAW_API_KEY`.
- **datagouv** (`https://mcp.data.gouv.fr/mcp`): search across the public
  data of data.gouv.fr. No authentication.

> **Confidentiality**: a `remote` MCP server **sends context outside the
> platform** (to the third-party service). Enable only knowingly and only
> with public / non-sensitive content.

To enable: rather than editing the global config, prefer a per-project
override — an `opencode.json` at the root of the repository concerned:

```json
{ "mcp": { "servers": { "datagouv": { "type": "remote", "url": "https://mcp.data.gouv.fr/mcp", "disabled": false } } } }
```

The `insee-public-data` skill documents this pattern and the non-MCP
alternatives (pynsee, R insee package, Parquet-first ingestion).

## Maintaining the vendored third-party skills

`THIRD_PARTY.md` documents the adapted DuckDB and MLflow skills. The MLflow ones are re-created from the revision
pinned in `UPSTREAM.lock`:

```bash
python3 -I scripts/vendor_mlflow_skills.py     # downloads the pinned revision, re-applies the Onyxia edits
git diff .opencode/skills                      # empty unless the pin or the script changed
```

To update, review the upstream diff, bump the SHA in `UPSTREAM.lock`, re-run the script (it fails loudly if an
edit no longer applies) and update `THIRD_PARTY.md`. The DuckDB skills are adapted by hand: port upstream changes
manually and re-test the snippets.

## Updating the global config

After a `git pull` of the repository, simply rerun:

```bash
./install.sh
```

## Notes

- OpenCode is not sandboxed: `shell` commands run on the pod. Routine commands run without
  prompts; `opencode.jsonc` asks for `rm`, `git push`, publishing to `diffusion/`, cluster mutations and uploads,
  and hard-denies `sudo`, remote deletions and every LLM provider except the self-hosted `onyxia` one
  (README, "Permissions"). Check changes with
  `python3 -I scripts/check_permissions.py`.
- The models being self-hosted, exchanges stay within the Insee perimeter.
- The gateway does not publish context/output token limits; the `limit` values
  in `opencode.jsonc` are conservative estimates. If long generations truncate
  or the context overflows sooner than expected, adjust them (ask the platform
  team for the deployed values).
- OpenCode's own auth credentials (`opencode auth login`) are stored outside
  the repository (`~/.local/share/opencode/`); they cannot be committed by
  accident.
