---
name: mlflow-tracking
description: Suivre des expériences et gérer des modèles avec l'instance MLflow partagée d'Onyxia/SSP Cloud — logging de paramètres/métriques/artefacts, autolog, signature de modèle, comparaison programmatique des runs (search_runs), registre de modèles et chargement, en Python et en R. À charger dès qu'on entraîne un modèle, compare des runs, ou que la tâche mentionne tracking, expérience, MLFLOW_TRACKING_URI, registre ou versionnage de modèles.
license: MIT
---

# Suivi d'expériences avec MLflow sur Onyxia

Lancer le service **MLflow** depuis le catalogue : il renseigne automatiquement
`MLFLOW_TRACKING_URI` (et `MLFLOW_S3_ENDPOINT_URL`) dans les services qui suivent.
Les métadonnées vont en PostgreSQL, les artefacts sur MinIO.

## Vérifier la configuration
```python
import os, mlflow
print(os.environ.get("MLFLOW_TRACKING_URI"))   # doit être renseignée
mlflow.set_experiment("nom-du-projet")          # crée/sélectionne l'expérience
```
Si `MLFLOW_TRACKING_URI` est absente, pointer manuellement vers l'URL du service
MLflow (forme `https://user-<namespace>-<id>.user.lab.sspcloud.fr`).

## Python — logging manuel
```python
import mlflow
from mlflow.models import infer_signature

with mlflow.start_run(run_name="rf-baseline"):
    mlflow.log_params({"n_estimators": 200, "max_depth": 8})
    # ... entraînement ...
    mlflow.log_metric("f1", f1)
    mlflow.log_metric("roc_auc", auc)
    # signature + input_example : schéma d'entrée/sortie vérifié au chargement
    mlflow.sklearn.log_model(model, artifact_path="model",
                             registered_model_name="mon_modele",
                             signature=infer_signature(X_train, model.predict(X_train)),
                             input_example=X_train.head(3))
    mlflow.log_artifact("figures/confusion_matrix.png")
```

## Python — autolog (le plus simple)
```python
import mlflow
mlflow.sklearn.autolog()      # ou xgboost / lightgbm / pytorch / keras
mlflow.set_experiment("nom-du-projet")
with mlflow.start_run():
    model.fit(X_train, y_train)   # params, métriques et modèle loggés tout seuls
```

## Python — comparer des runs programmatiquement
```python
import mlflow
runs = mlflow.search_runs(experiment_names=["nom-du-projet"],
                          order_by=["metrics.f1 DESC"], max_results=10)
best = runs.iloc[0]          # DataFrame pandas : run_id, params.*, metrics.*
print(best["run_id"], best["metrics.f1"])
```

## Registre de modèles : promouvoir et charger
```python
from mlflow import MlflowClient
client = MlflowClient()
# Charger une version par alias/stage
model = mlflow.pyfunc.load_model("models:/mon_modele@production")
preds = model.predict(X_new)
```
Versionner explicitement (alias `@champion`/`@production`) plutôt que de réécrire
une version ; garder la traçabilité données → run → modèle déployé.

## R — package mlflow
Le support R est plus limité que le support Python (pas d'autolog, API de
registre réduite) : pour un usage avancé, privilégier l'UI MLflow ou un script
Python d'appoint.
```r
library(mlflow)
mlflow_set_experiment("nom-du-projet")
with(mlflow_start_run(), {
  mlflow_log_param("alpha", 0.3)
  # ... entraînement ...
  mlflow_log_metric("rmse", rmse)
  mlflow_log_model(model, "model")
})
```

## Diagnostic / erreurs fréquentes
- `MLFLOW_TRACKING_URI` absente → aucun service MLflow ne tournait à la création
  du service courant : lancer MLflow depuis le catalogue puis relancer le service,
  ou pointer manuellement vers son URL.
- `403 AccessDenied` à l'écriture d'un artefact → jeton S3 expiré (7 jours),
  cf. skill `onyxia-storage-s3`.

## Bonnes pratiques
- Une **expérience par problème métier**, un **run par configuration**.
- Logger systématiquement : version du code (commit Git), jeu de données (chemin
  S3 + éventuel hash), seed, environnement (`uv.lock`/`renv.lock`), paramètres du
  script (arguments, fichier de configuration).
- Toujours fournir `signature` et `input_example` à `log_model` : le schéma
  d'entrée est alors validé au chargement/serving.
- Pour comparer beaucoup de configurations en parallèle → passer la main au
  workflow Argo (cf. skill `argo-mlops`).
