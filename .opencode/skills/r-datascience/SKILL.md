---
name: r-datascience
description: Standards de projet R data science sur Onyxia, alignés sur la documentation utilitR de l'Insee — qualité du code (lintr, styler, fonctions, notation package::fonction), structure de projet (projets RStudio, sous-dossiers, README), environnement figé renv, pipelines targets, Parquet via arrow/duckdb, accès S3 via aws.s3/arrow, modélisation tidymodels. À charger pour créer/structurer un projet R, écrire un pipeline R, produire du code R propre, ou dès que la tâche mentionne renv.lock, targets, .Rproj, lintr, styler ou tidymodels.
license: MIT
---

# Standards projet R (data science) sur Onyxia

Référence de fond : **utilitR** (book.utilitr.org), la documentation collaborative
de l'Insee sur les bonnes pratiques R.

## Qualité du code (utilitR « Qualité du code »)
- **Style** : suivre le *tidyverse style guide*, de façon cohérente dans tout le projet.
  - *linter* : `lintr::use_lintr(type = "tidyverse")` puis `lintr::lint_dir()`.
  - *formatter* : `styler::style_dir()` (ou `styler::style_file()`).
- **DRY** : dès qu'une portion de code sert plus de deux fois, en faire une fonction.
  *Une tâche = une fonction* ; une tâche complexe = un enchaînement de fonctions
  simples ; limiter les variables globales (éviter le « code spaghetti »).
- **Documentation** : documenter le *pourquoi* plutôt que le *comment* ; privilégier
  l'auto-documentation par des noms explicites ; documenter les fonctions en `roxygen2`.
- **Lever l'ambiguïté sur les packages** : `library()` pour les packages très
  utilisés ; sinon notation `package::fonction()`, surtout en cas de conflit de noms
  (ex. `dplyr::select` vs `MASS::select`). Le package `conflicted` aide à les gérer.

## Structure des projets (utilitR « Structure des projets »)
- Toujours un **projet RStudio** (chemins relatifs, working directory automatique).
- **Sous-dossiers thématiques**, séparant entrées / intermédiaires / sorties :
```
projet/
├── data/
│   ├── raw/         # données de base, immuables
│   └── derived/     # tables intermédiaires produites par le code
├── scripts/         # traitements (import, nettoyage…)
├── analysis/        # analyses + rapports (.qmd / .Rmd)
├── output/          # sorties RE-GÉNÉRABLES (figures, rapports)
├── R/               # fonctions du projet
└── README.md        # carte d'identité du projet (contexte, objectifs, usage)
```
- **Noms de fichiers signifiants**, **sans espace ni accent** (sources d'erreurs).
- Données volumineuses sur S3, pas dans Git (skill `onyxia-storage-s3`).

## Environnement figé — renv
`renv::init()` au démarrage du projet, `renv::snapshot()` après chaque ajout de
package : `renv.lock` est commité (jamais `renv/library/`), `renv::restore()`
reconstitue l'environnement à l'identique.

## Chaîne de traitement reproductible — targets
`targets` matérialise le pipeline en graphe de dépendances ; seules les étapes
impactées sont recalculées (`_targets.R`, `tar_make()`, `tar_visnetwork()`).
À réserver aux pipelines qui le justifient (plusieurs étapes coûteuses,
dépendances non triviales) — pour un enchaînement simple, des scripts numérotés
suffisent.

## Données : Parquet via arrow / duckdb
utilitR recommande `arrow` (et `duckdb`) pour le Parquet, y compris sur S3 et en
lecture paresseuse (`open_dataset() |> filter() |> ... |> collect()`).
`data.table` pour la performance en mémoire, `tidyverse` pour la lisibilité.

## Modélisation — tidymodels
```r
library(tidymodels)
rec  <- recipe(cible ~ ., data = train) |> step_normalize(all_numeric_predictors())
spec <- rand_forest(trees = 500) |> set_engine("ranger") |> set_mode("classification")
wf   <- workflow() |> add_recipe(rec) |> add_model(spec)
fit  <- fit(wf, data = train)
```
Suivre les essais via le package `mlflow` (skill `mlflow-tracking`).

## Références
- book.utilitr.org (notamment « Qualité du code » et « Structure des projets »)
- Formation Insee bonnes pratiques R : inseefrlab.github.io/formation-bonnes-pratiques-git-R
- Workflow Git (`.gitignore`, commits, PR) : skill `git-workflow-ds` ;
  restitution `.qmd` : skill `quarto-publication`.
