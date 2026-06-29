# Contexte projet — Datascience sur Onyxia

Ce dépôt est travaillé depuis un service interactif (VSCode, Jupyter ou RStudio)
lancé sur **Onyxia** — la plateforme de data science développée par l'Insee,
déployée ici sur le **SSP Cloud** (`datalab.sspcloud.fr`). Tous les agents
doivent connaître et exploiter cet environnement plutôt que de proposer des
solutions « cloud générique ».

## Principes directeurs
- **Reproductibilité d'abord** : tout doit pouvoir être rejoué à l'identique
  (lockfiles, conteneurs, pipelines déclaratifs, données sur S3, code sous Git).
- **Open source** : R, Python, Quarto, Git ; pas de dépendance propriétaire.
- **Confidentialité** : sur l'instance publique, seules des données publiques /
  non sensibles sont autorisées. Ne jamais écrire de secret en clair dans le code.
  Les LLM utilisés ici sont **auto-hébergés sur la plateforme** : les données
  envoyées aux agents restent dans le périmètre sspcloud.
- **Du prototype à la production** : on vise le cycle MLOps complet
  (expérimentation → packaging → déploiement → supervision).

## Plateforme : ce qui est déjà fourni et préconfiguré
- **Kubernetes** sous-jacent ; chaque service est un *chart Helm* du catalogue
  (`inseefrlab/...`). Les services exposés ont une URL de la forme
  `https://user-<namespace>-<id>.user.lab.sspcloud.fr`.
- **Stockage S3 = MinIO** (compatible API S3 d'Amazon). Le bucket personnel
  porte le nom d'utilisateur. Le dossier `diffusion/` à la racine d'un bucket
  est **accessible en lecture à tous** les utilisateurs (mécanisme de partage).
- **Vault** pour les secrets (tokens, mots de passe), injectés comme variables
  d'environnement dans les services.
- **MLflow** : instance partagée pour le suivi d'expériences et le registre de
  modèles (métadonnées en PostgreSQL, artefacts sur MinIO).
- **Argo Workflows** (orchestration de tâches parallèles sur K8s) et **ArgoCD**
  (déploiement continu en GitOps) pour l'industrialisation.
- **duckdb** disponible dans tous les services interactifs, préférer son utilisation 
  pour les traitements.

## Variables d'environnement injectées automatiquement
À LIRE depuis l'environnement, JAMAIS à coder en dur :

| Variable | Rôle |
|---|---|
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | jeton S3/MinIO temporaire |
| `AWS_DEFAULT_REGION` | région (souvent `us-east-1` côté MinIO) |
| `AWS_S3_ENDPOINT` | hôte MinIO (ex. `minio.lab.sspcloud.fr`) |
| `MLFLOW_TRACKING_URI` | renseignée quand un service MLflow tourne |
| `MLFLOW_S3_ENDPOINT_URL` | endpoint S3 pour les artefacts MLflow |

> **Expiration du jeton S3 (~5–7 jours)** : un jeton périmé provoque une erreur
> **403** sur MinIO et le service apparaît en rouge dans « Mes services ». Remèdes :
> relancer un service (nouveau jeton) ou réinjecter des jetons frais. Si un agent
> voit un 403 sur S3, suspecter l'expiration avant tout autre diagnostic.

## Accès aux données (résumé — détails dans la skill `onyxia-storage-s3`)

Endpoint MinIO du SSP Cloud : `https://minio.lab.sspcloud.fr` (= `$AWS_S3_ENDPOINT`).
**Règle Onyxia** : ne pas télécharger les fichiers dans le conteneur, **ingérer la
donnée directement en mémoire** depuis S3 ; ne copier en local que si nécessaire.

- **Python** : `s3fs` pour lire/écrire en mémoire ; `duckdb` pour le
  Parquet volumineux (lecture paresseuse, *predicate pushdown*).
- **R** : `duckdb` (lecture Parquet/dataset sur S3) ou `aws.s3` (les variables AWS_* suffisent).
- **Terminal** : **`aws s3`** est la CLI à privilégier (le client `mc` existe aussi) :
  `aws --endpoint-url "https://$AWS_S3_ENDPOINT" s3 ls s3://$USERNAME/`.

## Conventions de travail attendues
- Python : projet géré par **`uv`** (`pyproject.toml` + `uv.lock`), formaté/linté
  avec **`ruff`**, testé avec **`pytest`**. Préférer `polars`/`duckdb` pour la volumétrie.
- R : environnement figé par **`renv`**, pipelines avec **`targets`** uniquement si strictement nécessaires, tests avec
  **`testthat`**, style `tidyverse`/`styler`.
- Données : pas de gros fichiers dans Git → tout sur S3 ; chemins paramétrés.
- Documentation et restitution : **Quarto**.
- Aucun secret commité. Pas de données dans le dépôt.

## Références internes (faisant autorité)
- Doc plateforme SSP Cloud : https://docs.sspcloud.fr
- Guide utilisateur Onyxia : https://docs.onyxia.sh/user-doc/user-guide
- **R** — utilitR (bonnes pratiques Insee) : https://book.utilitr.org
- **Python** — « Python pour la data science » (L. Galiana) : https://pythonds.linogaliana.fr
- MLOps : https://github.com/InseeFrLab/formation-mlops
- Mise en production / reproductibilité : https://ensae-reproductibilite.github.io/website
- Images Docker data science : https://github.com/inseefrlab/images-datascience

Quand une tâche relève d'un domaine outillé, **charge la skill correspondante**
(`onyxia-storage-s3`, `mlflow-tracking`, `argo-mlops`, `r-datascience`,
`python-datascience`, `reproductibilite-onyxia`) avant de produire du code.
