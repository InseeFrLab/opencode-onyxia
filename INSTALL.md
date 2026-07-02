# INSTALL — Configuration OpenCode GLOBALE (valable pour tous les projets)

Cette configuration s'installe **au niveau global** dans `~/.config/opencode/`.
Elle s'applique alors à **tous vos projets**, sur n'importe quel service interactif
(VSCode-python, Jupyter, RStudio) lancé sur le SSP Cloud — sans avoir à la recopier
dans chaque dépôt.

Arborescence cible une fois installé :

```txt
~/.config/opencode/
├── opencode.jsonc      # fournisseur, modèles, agents, permissions
├── AGENTS.md           # contexte Onyxia appliqué à TOUTES les sessions
├── prompts/*.md        # prompts système des agents
└── skills/*/SKILL.md   # skills globales (NB : ici sans le préfixe .opencode)
```

---

## 1. Installer OpenCode

```bash
curl -fsSL https://opencode.ai/install | bash
opencode --version
```

## 2. Obtenir une clé d'API Open WebUI

Dans `https://llm.lab.sspcloud.fr` : menu profil -> **Settings** -> **Account** ->
**API Keys** -> générer/afficher une clé (format `sk-...`).

## 3. Renseigner les deux variables d'environnement (une fois pour toutes)

Les mettre dans `~/.bashrc` pour qu'elles s'appliquent à tous les services :

```bash
echo 'export OPENAI_BASE_URL="https://llm.lab.sspcloud.fr/v1"' >> ~/.bashrc
echo 'export OPENAI_API_KEY="sk-……"' >> ~/.bashrc
source ~/.bashrc
```

> Open WebUI expose `/v1` (couche OpenAI-compatible, attendue par OpenCode) *et*
> `/api` (API native). Si `…/v1/chat/completions` répond `404`, utiliser `…/api`
> en repli (test `curl` à l'étape 4 du README).

> Recommandé : stocker la clé dans **Vault** (onglet « Mes secrets » d'Onyxia) et
> l'injecter comme variable d'environnement à la création des services — la clé
> n'apparaît alors jamais en clair.

## 4. Installer la config en global

### Méthode A — script fourni (recommandée)

Depuis le dossier décompressé du dépôt :

```bash
cd opencode-onyxia
./install.sh
```

Le script copie `opencode.jsonc`, `AGENTS.md`, `prompts/` dans `~/.config/opencode/`,
et les skills dans `~/.config/opencode/skills/` (il sauvegarde une config existante).

### Méthode B — manuelle

```bash
cd opencode-onyxia
mkdir -p ~/.config/opencode/prompts ~/.config/opencode/skills
cp  opencode.jsonc AGENTS.md  ~/.config/opencode/
cp -r prompts/.               ~/.config/opencode/prompts/
cp -r .opencode/skills/.      ~/.config/opencode/skills/
```

### Méthode C — suivre le dépôt en Git (mise à jour facile par `git pull`)

```bash
git clone <url-du-depot> ~/opencode-onyxia
cd ~/opencode-onyxia && ./install.sh
# pour mettre à jour plus tard :  cd ~/opencode-onyxia && git pull && ./install.sh
```

> On ne clone pas directement *dans* `~/.config/opencode` : les skills globales
> doivent vivre dans `~/.config/opencode/skills/` (sans le `.opencode/` qu'utilise
> une config de *projet*). Le script gère ce détail.


## 5. Utiliser, depuis n'importe quel projet

```bash
cd ~/work/mon-projet-quelconque
opencode
```

- `/models` -> `qwen3-6-35b-moe`, `gemma4-26b-moe`, `qwen3-vl` sous
  « SSPCloud LLM (auto-hébergé) ».
- **Tab** -> bascule `build` <-> `plan`.
- `@python-ds`, `@r-ds`, `@mlops`, `@reviewer`, `@dataviz-vision` -> sous-agents
  (aussi délégués automatiquement). Les skills se chargent selon le contexte.

La config globale s'applique partout ; aucune installation par projet n'est nécessaire.

---

## Surcharger ponctuellement dans un projet (optionnel)

La config de projet a priorité sur la globale et **se combine** avec elle. Dans un
dépôt donné, vous pouvez :

- ajouter un `AGENTS.md` à la racine -> instructions spécifiques au projet (s'ajoutent au contexte global) ;
- ajouter `.opencode/skills/<nom>/SKILL.md` -> skills propres au projet ;
- ajouter un `opencode.json` à la racine -> réglages qui priment sur le global
  (ex. changer le modèle par défaut, restreindre des permissions).

## Serveurs MCP (optionnels, désactivés par défaut)

`opencode.jsonc` pré-déclare deux serveurs MCP `remote` avec `"enabled": false` :

- **excalidraw** (`https://api.excalidraw.com/api/v1/mcp`) : création de
  diagrammes. Nécessite une clé dans `EXCALIDRAW_API_KEY`.
- **datagouv** (`https://mcp.data.gouv.fr/mcp`) : recherche dans les données
  publiques de data.gouv.fr. Sans authentification.

> **Confidentialité** : un serveur MCP `remote` **envoie du contexte hors de la
> plateforme** (vers le service tiers). N'activer qu'en connaissance de cause et
> uniquement avec des contenus publics / non sensibles.

Pour activer : plutôt que de modifier la config globale, préférer une surcharge
par projet — un `opencode.json` à la racine du dépôt concerné :

```json
{ "mcp": { "datagouv": { "type": "remote", "url": "https://mcp.data.gouv.fr/mcp", "enabled": true } } }
```

## Mettre à jour la config globale

Après un `git pull` du dépôt, relancer simplement :

```bash
./install.sh
```

## Notes

- OpenCode n'est pas sandboxé : `bash` s'exécute sur le pod. Les permissions de
  `opencode.jsonc` demandent confirmation pour le réseau, k8s et `rm`.
- Les modèles étant auto-hébergés, les échanges restent dans le périmètre Insee.
- Les identifiants d'authentification d'OpenCode (`opencode auth login`) sont stockés
  hors du dépôt (`~/.local/share/opencode/`), ils ne risquent pas d'être commités.
