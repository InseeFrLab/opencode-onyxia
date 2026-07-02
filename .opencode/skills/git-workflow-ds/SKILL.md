---
name: git-workflow-ds
description: Workflow Git pour projets de data science à l'Insee — .gitignore adapté (données, environnements, sorties, .env), commits atomiques et messages clairs, branches courtes et merge/pull requests, gestion des notebooks (nbstripout), interdits absolus (secrets, données, gros binaires) et remédiation si un secret a été commité. À charger pour initialiser un dépôt, écrire un message de commit, préparer une PR/MR, nettoyer un historique, ou configurer un .gitignore.
license: MIT
---

# Workflow Git pour la data science

Git versionne **le code, rien que le code** : pas de données, pas de secrets,
pas de sorties re-générables. Référence : formation Insee
« bonnes pratiques Git » et utilitR.

## `.gitignore` type d'un projet data science
```gitignore
# Données (elles vivent sur S3, skill onyxia-storage-s3)
data/
*.parquet
*.csv

# Environnements (reconstruits depuis les lockfiles)
.venv/
renv/library/
renv/staging/

# Sorties re-générables
output/
_targets/
_site/
*.html

# Secrets et configuration locale
.env
.Renviron

# Bruit
.Rhistory
.RData
.ipynb_checkpoints/
__pycache__/
```
On **commite** en revanche : `pyproject.toml` + `uv.lock`, `renv.lock`,
`conf/config.yaml` (sans secret), le `README.md`.

## Commits
- **Atomiques** : un commit = un changement cohérent (pas de « wip divers »).
- Message à l'**impératif**, première ligne ≤ 72 caractères ; convention légère
  type Conventional Commits appréciée :
  ```
  feat: ajoute la lecture partitionnée du RP depuis S3
  fix: corrige la seed du split train/test
  docs: complète le README (lancement du pipeline)
  ```
- Commiter souvent ; ne jamais commiter un état qui casse le pipeline principal.

## Branches et relecture
- `main` reste stable/protégée ; une **branche courte par sujet**
  (`feat/lecture-s3`, `fix/seed`), fusionnée vite via merge/pull request.
- Avant de fusionner : relire le diff (déléguer à `@reviewer`), vérifier
  qu'aucun fichier de données/sortie ne s'est glissé dans le diff (`git status`).

## Notebooks
Les sorties de cellules polluent les diffs et peuvent contenir des données :
```bash
uvx nbstripout --install        # filtre Git : vide les sorties au commit
```
Mieux : la logique de production sort du notebook vers `src/` ou `R/`
(skills `python-datascience` / `r-datascience`) ; le notebook reste exploratoire.

## Interdits absolus
- **Secret** (clé d'API, mot de passe, token) — même « temporairement » :
  utiliser Vault (skill `vault-secrets-onyxia`).
- **Données**, même petites : Git n'est pas un stockage de données → S3.
- **Gros binaires** (> quelques Mo) : ils restent pour toujours dans l'historique.

## Remédiation : un secret a été commité
1. **Révoquer le secret d'abord** (rotation) — il est compromis dès le push,
   purger l'historique ne suffit pas.
2. Purger l'historique :
   ```bash
   git filter-repo --invert-paths --path chemin/du/fichier
   git push --force-with-lease
   ```
3. Prévenir les co-contributeurs (leurs clones contiennent encore le secret) et
   recréer le secret dans Vault.

## Références
- Formation Insee : https://inseefrlab.github.io/formation-bonnes-pratiques-git-R
- utilitR, chapitres Git : https://book.utilitr.org
- https://github.com/newren/git-filter-repo
