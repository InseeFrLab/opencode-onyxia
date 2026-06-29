# Configuration OpenCode multi-agents pour Onyxia (Insee)

Configuration prête à l'emploi pour piloter, depuis OpenCode, des projets de
**data science et MLOps en R et Python** dans l'environnement **Onyxia / SSP Cloud**,
en s'appuyant sur les **modèles auto-hébergés** de la plateforme (les données
envoyées aux agents restent donc dans le périmètre Insee).

## Contenu
```
opencode-onyxia/
├── opencode.jsonc                 # config principale : fournisseur, modèles, agents, permissions, MCP
├── AGENTS.md                      # contexte Onyxia partagé par TOUS les agents (chargé automatiquement)
├── install.sh                     # installation GLOBALE dans ~/.config/opencode (tous projets)
├── INSTALL.md                     # guide d'installation détaillé
├── prompts/                       # prompt système de chaque agent
│   ├── build.md  plan.md  python-ds.md  r-ds.md  mlops.md  reviewer.md  dataviz-vision.md
└── .opencode/skills/              # savoir-faire chargés à la demande (1 dossier = 1 skill)
    ├── onyxia-storage-s3/SKILL.md
    ├── mlflow-tracking/SKILL.md
    ├── argo-mlops/SKILL.md
    ├── python-datascience/SKILL.md
    ├── r-datascience/SKILL.md
    └── reproductibilite-onyxia/SKILL.md
```

## Installation (résumé — guide détaillé dans `INSTALL.md`)
1. **Installer OpenCode** dans le service (VSCode/Jupyter) :
   ```bash
   curl -fsSL https://opencode.ai/install | bash
   ```
2. **Installer la config en global** (valable pour tous les projets) — script fourni :
   ```bash
   cd opencode-onyxia && ./install.sh
   ```
   Il copie la config, `AGENTS.md`, les prompts et les skills dans
   `~/.config/opencode/`. Détails et alternatives (manuel, suivi Git, surcharge
   par projet) dans **`INSTALL.md`**.
3. **Récupérer une clé d'API** sur la passerelle Open WebUI
   `https://llm.lab.sspcloud.fr` (Settings → Account → API Keys), puis renseigner
   les deux variables d'environnement :
   ```bash
   export OPENAI_BASE_URL="https://llm.lab.sspcloud.fr/v1"
   export OPENAI_API_KEY="sk-……"
   ```
   (Idéalement stockées dans Vault et injectées par le service.)
4. **Vérifier l'endpoint** (Open WebUI expose `/v1` *et* `/api`) :
   ```bash
   curl -s "$OPENAI_BASE_URL/chat/completions" \
     -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
     -d '{"model":"qwen3-6-35b-moe","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
   ```
   Réponse `chat.completion` → `/v1` est correct ; `404` → utiliser `…/api`.
   Les identifiants de modèles (`qwen3-6-35b-moe`, `gemma4-26b-moe`, `qwen3-vl`)
   sont déjà confirmés et présents dans la config.
5. **Lancer** : `opencode` puis `/models` pour confirmer la présence des modèles.

## Utilisation
- **Basculer entre agents principaux** (`build` ⇄ `plan`) : touche **Tab**.
- **Déléguer** : les sous-agents (`python-ds`, `r-ds`, `mlops`, `reviewer`,
  `dataviz-vision`) sont appelés automatiquement selon le besoin, ou explicitement
  via `@nom` (ex. `@reviewer relis le diff`, `@mlops déploie ce modèle`).
- **Skills** : chargées automatiquement quand la tâche correspond à leur description ;
  on peut aussi y faire référence dans le prompt.

## Répartition des modèles
| Modèle | Rôle dans la config |
|---|---|
| `qwen3-6-35b-moe` | modèle par défaut — code, raisonnement, agents `build`/`python-ds`/`r-ds`/`mlops` |
| `gemma4-26b-moe` | `small_model` (titres, résumés) + agents `plan` et `reviewer` (diversité de point de vue) |
| `qwen3-vl` | agent `dataviz-vision` — lecture de graphiques, schémas, captures |
| `qwen3-embedding-8b` | **embeddings** — voir ci-dessous |

### Embeddings (`qwen3-embedding-8b`)
Ce n'est pas un modèle de chat : il ne peut pas piloter un agent. Il sert à la
**recherche sémantique / RAG** (indexer une base de code ou de documentation
méthodologique et retrouver les passages pertinents). Pour l'exploiter, le brancher
derrière un outil ou un serveur MCP de recherche (clé `mcp` de `opencode.jsonc`)
pointant sur l'endpoint d'embeddings — à activer seulement si un cas d'usage le justifie.

## Sécurité / confidentialité
- OpenCode n'est pas sandboxé : les commandes `bash` s'exécutent réellement sur le pod.
  Les permissions de `opencode.jsonc` autorisent l'outillage data science usuel et
  **demandent confirmation** pour le réseau, Kubernetes et les suppressions.
- MCP désactivé par défaut (un MCP « remote » enverrait du contexte hors plateforme).
- Sur l'instance publique, ne traiter que des données publiques / non sensibles.

## Personnalisation
- Ajouter un agent : nouveau bloc sous `agent` + un prompt dans `prompts/`.
- Ajouter un savoir-faire : nouveau dossier `.opencode/skills/<nom>/SKILL.md`
  (en-tête YAML `name` + `description` obligatoires).
- Les skills suivent le standard Agent Skills : celles écrites pour Claude Code
  fonctionnent telles quelles.
