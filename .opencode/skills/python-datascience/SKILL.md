---
name: python-datascience
description: Standards de projet Python data science / ML sur Onyxia, alignés sur "Python pour la data science" (Lino Galiana, ENSAE) — environnement uv, qualité ruff, tests pytest, manipulation pandas/polars, lecture performante de Parquet avec pyarrow/duckdb, pipelines scikit-learn, mise à disposition via FastAPI. À charger pour créer/structurer un projet Python, choisir des librairies, écrire du code Python ML propre, ou dès que la tâche mentionne pyproject.toml, uv.lock, un notebook à industrialiser, ruff, pytest ou scikit-learn.
license: MIT
---

# Standards projet Python (data science / ML) sur Onyxia

Référence de fond : **« Python pour la data science »** de Lino Galiana
(pythonds.linogaliana.fr), cours ENSAE/Ensai, conçu autour du SSP Cloud.

## Environnement & outillage — uv
`uv` est le gestionnaire recommandé (lockfile déterministe, rapide).
```bash
uv init mon-projet && cd mon-projet
uv add polars pandas pyarrow duckdb scikit-learn mlflow s3fs
uv add --dev ruff pytest mypy
uv run python scripts/train.py
uv sync                         # reconstitue l'env depuis uv.lock (reproductible)
```
`pyproject.toml` + `uv.lock` sont commités ; jamais le `.venv/`.

## Qualité de code
```bash
uv run ruff format .            # formatage
uv run ruff check --fix .       # lint + corrections sûres
uv run pytest -q                # tests
uv run mypy src/                # typage progressif
```

## Manipulation de données : le bon outil selon la volumétrie
- **pandas** : confort, petits/moyens volumes, écosystème riche.
- **polars** : DataFrames rapides, *lazy* (`scan_*`) sur gros volumes.
- **Parquet plutôt que CSV** : colonnaire, compressé, typé. Pour en tirer parti
  (lecture de colonnes seules, *predicate pushdown*), lire avec **pyarrow.dataset**
  ou **duckdb** plutôt que de tout charger en `DataFrame` :
```python
import pyarrow.dataset as ds, pyarrow.compute as pc
table = (ds.dataset("data/RP_partitionne", partitioning="hive")
           .to_table(filter=pc.field("DEPT").isin(["18","36"]), columns=["AGED","IPONDI","DEPT"]))
df = table.to_pandas()
```
```python
import duckdb
duckdb.sql("FROM read_parquet('data/RP.parquet') SELECT AGED, SUM(IPONDI) GROUP BY AGED").to_df()
```
- **Partitionner** un Parquet (`pq.write_to_dataset(..., partition_cols=[...])`)
  quand on filtre souvent sur une variable. Accès S3 : skill `onyxia-storage-s3`.

## Modélisation — scikit-learn
- Encapsuler tout le prétraitement dans un `Pipeline` + `ColumnTransformer`
  (évite les fuites de données, rend le modèle déployable d'un bloc).
- Séparer train/valid/test, fixer une seed, valider par validation croisée,
  évaluer avec une métrique adaptée au problème (pas seulement l'accuracy).
- Suivre chaque essai avec MLflow (skill `mlflow-tracking`).

## Mise à disposition d'un modèle — FastAPI
Exposer la prédiction via une API **FastAPI** (chargée depuis le registre MLflow),
puis conteneuriser et déployer (skill `argo-mlops`). Voir le chapitre
« Mettre à disposition un modèle par le biais d'une API » de la référence.

## Structure conseillée
```
mon-projet/
├── pyproject.toml / uv.lock
├── src/mon_projet/        # code importable (data.py, features.py, model.py)
├── scripts/               # entrées paramétrées (train.py, predict.py)
├── tests/
├── conf/                  # paramètres (YAML), PAS de secret
└── notebooks/             # exploration uniquement (logique de prod -> src/)
```

## Principes (issus de la référence)
Code modulaire (fonctions courtes et testables), séparation stricte code / config /
données (Git ≠ stockage de données → tout sur S3), chemins paramétrés jamais en dur,
notebooks réservés à l'exploration. Git est indispensable — `.gitignore`, commits,
notebooks : skill `git-workflow-ds`. Restitution des résultats : skill
`quarto-publication`.
