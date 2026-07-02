---
name: reproductibilite-onyxia
description: Bonnes pratiques de reproductibilité et de portabilité d'un projet de data science sur Onyxia/SSP Cloud — structure de projet, conteneurisation (Dockerfile à partir des images Insee), lockfiles, paramétrage, gestion des secrets via Vault, restitution avec Quarto, workflow Git. À charger pour cadrer la structure d'un projet, le rendre reproductible, ou préparer son passage à l'échelle/en production.
license: MIT
---

# Reproductibilité & portabilité sur Onyxia

Objectif : un projet rejouable à l'identique par un tiers, sur un autre service,
sans configuration manuelle. C'est le prérequis de toute mise en production.

## Les quatre piliers
1. **Code sous Git** — tout le code, rien que le code (pas de données, pas de
   secret) ; `.gitignore`, commits et PR : skill `git-workflow-ds`.
2. **Environnement figé** — `uv.lock` (Python) ou `renv.lock` (R) commités ;
   idéalement un `Dockerfile` pour figer aussi le système.
3. **Données externalisées** — sur S3/MinIO, jamais dans le dépôt ; chemins
   paramétrés (config), pas codés en dur (skill `onyxia-storage-s3`).
4. **Exécution déclarative** — un pipeline (`targets` en R, ou orchestration Argo)
   plutôt qu'une suite de cellules de notebook à lancer dans le bon ordre.

## Conteneurisation
Partir d'une image de base du catalogue Insee, qui contient déjà R/Python et
l'outillage data science préconfiguré pour S3 :
```dockerfile
FROM inseefrlab/python-datascience:latest
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
CMD ["uv", "run", "python", "scripts/train.py"]
```
L'image est reconstruite et publiée par CI (GitHub Actions) ; elle est ensuite
réutilisée par les workflows Argo et les déploiements (skill `argo-mlops`).

## Secrets : jamais en clair
Les credentials arrivent toujours par variables d'environnement ; les secrets
propres au projet vont dans **Vault** — détails, CLI et injection : skill
`vault-secrets-onyxia`.

## Paramétrage
Centraliser les paramètres (chemins S3, hyperparamètres, noms d'expérience) dans
un fichier de configuration (`conf/config.yaml`) ou en arguments de ligne de
commande. Un même code doit tourner en dev et en prod en changeant seulement la config.

## Restitution — Quarto
Documenter analyses et résultats en `.qmd` (code exécutable versionné avec le
rapport) — rédaction, rendu et publication : skill `quarto-publication`.

## Anti-patterns à signaler en revue
- Notebook monolithique destiné à la production (extraire la logique vers `src/`/`R/`).
- Chemins absolus locaux ; données dans le dépôt ; credentials en dur.
- Environnement non figé (« ça marche chez moi »).
- Étapes manuelles non scriptées entre l'entraînement et le déploiement.

## Référence
- Guide complet « Mise en production de projets data science » :
  https://ensae-reproductibilite.github.io/website
- Structure & qualité de projet R (utilitR, Insee) : https://book.utilitr.org
- Guide utilisateur Onyxia : https://docs.onyxia.sh/user-doc/user-guide
