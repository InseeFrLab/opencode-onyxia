---
name: mlflow-tracking
description: Suivre des expériences et gérer des modèles avec l'instance MLflow partagée d'Onyxia/SSP Cloud — logging de paramètres/métriques/artefacts, autolog, registre de modèles et chargement, en Python et en R. À charger dès qu'on entraîne un modèle, compare des runs, parle de tracking, d'expériences ou de registre de modèles.
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

with mlflow.start_run(run_name="rf-baseline"):
    mlflow.log_params({"n_estimators": 200, "max_depth": 8})
    # ... entraînement ...
    mlflow.log_metric("f1", f1)
    mlflow.log_metric("roc_auc", auc)
    mlflow.sklearn.log_model(model, artifact_path="model",
                             registered_model_name="mon_modele")
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

## Bonnes pratiques
- Une **expérience par problème métier**, un **run par configuration**.
- Logger systématiquement : version du code (commit Git), jeu de données (chemin
  S3 + éventuel hash), seed, environnement (`uv.lock`/`renv.lock`), parametres du 
  script (arguments, fichier de configurations)
- Les artefacts atterrissent sur MinIO : vérifier que les variables AWS_* sont
  valides (cf. skill `onyxia-storage-s3`, erreur 403 = jeton expiré).
- Pour comparer beaucoup de configurations en parallèle → passer la main au
  workflow Argo (cf. skill `argo-mlops`).
