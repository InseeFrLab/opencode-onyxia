---
name: quarto-publication
description: Rédiger et publier des documents Quarto (.qmd) sur Onyxia — rapports HTML/PDF, présentations reveal.js, dashboards, sites et livres ; code R et Python exécutable, documents paramétrés, publication vers S3 (dossier diffusion/) ou GitHub Pages. À charger dès qu'il faut produire un rapport, une notice, une présentation, un dashboard ou de la documentation, ou que la tâche mentionne Quarto, .qmd, un .Rmd à migrer, ou un rendu HTML/PDF.
license: MIT
---

# Rédiger et publier avec Quarto sur Onyxia

Quarto est l'outil de restitution recommandé (AGENTS.md) : le code (R et/ou
Python) reste exécutable et versionné **avec** le rapport. Un `.Rmd` existant se
migre généralement en renommant en `.qmd` et en adaptant l'en-tête.

> **Règle d'or** : le rendu est **re-générable** (`quarto render`) — jamais de
> résultat copié-collé à la main, jamais de secret ni de donnée sensible dans
> le document rendu.

## Anatomie d'un `.qmd`
````markdown
---
title: "Analyse RP"
author: "Prénom Nom"
format:
  html:
    toc: true
    code-fold: true
execute:
  echo: true
  warning: false
  freeze: auto        # fige les résultats des chunks non modifiés (reproductible)
---

## Contexte

```{r}
library(dplyr)
# ... code R exécuté au rendu ...
```

```{python}
import polars as pl
# ... R et Python peuvent coexister dans le même document ...
```
````
Les données se lisent **depuis S3** (skill `onyxia-storage-s3`), jamais depuis
un chemin local en dur.

## Terminal — rendre et prévisualiser
```bash
quarto render rapport.qmd             # -> rapport.html (ou pdf selon format)
quarto render rapport.qmd --to pdf
quarto preview rapport.qmd            # rendu live pendant la rédaction
```

## Projets : site, livre, dashboard
Un `_quarto.yml` à la racine transforme le dossier en projet :
```yaml
project:
  type: website        # ou book, ou default
website:
  title: "Mon projet"
  navbar:
    left: [index.qmd, analyse.qmd]
```
- Présentation : `format: revealjs` dans l'en-tête du `.qmd`.
- Dashboard : `format: dashboard` (composants `valuebox`, lignes/colonnes).

## Documents paramétrés
```yaml
params:
  annee: 2024
  dept: "31"
```
Accès dans le code : `params$annee` (R) / balise `#| tags: [parameters]` puis
`annee` (Python). Rendu avec d'autres valeurs :
```bash
quarto render rapport.qmd -P annee:2025 -P dept:11
```
Un même rapport sert ainsi plusieurs millésimes/départements sans duplication.

## Publier
```bash
# 1) Vers le dossier public de son bucket (lisible par tout utilisateur authentifié)
quarto render rapport.qmd
aws --endpoint-url "https://$AWS_S3_ENDPOINT" s3 cp rapport.html "s3://$USERNAME/diffusion/"
# site complet : aws ... s3 sync _site/ "s3://$USERNAME/diffusion/mon-site/"

# 2) Vers GitHub Pages (projet website/book)
quarto publish gh-pages
```

## Diagnostic / erreurs fréquentes
- `quarto: command not found` → l'image du service ne l'embarque pas ; utiliser
  une image datascience Insee récente (`inseefrlab/...`) qui l'inclut.
- Rendu PDF échoue → moteur LaTeX manquant : `quarto install tinytex`.
- Chunk Python non exécuté dans un projet R → package `reticulate` requis quand
  R et Python coexistent (sinon `engine: jupyter`).

## Garde-fous
- `freeze: auto` en projet : évite de ré-exécuter des chunks coûteux non modifiés.
- Le `.qmd` est commité ; le rendu (`.html`, `_site/`) va dans `output/` ou sur
  S3, pas dans Git (skill `git-workflow-ds`).
- Relire le rendu avant publication : pas de secret, pas de donnée individuelle.

## Références
- https://quarto.org/docs/guide/
- utilitR, partie « Produire des documents » : https://book.utilitr.org
