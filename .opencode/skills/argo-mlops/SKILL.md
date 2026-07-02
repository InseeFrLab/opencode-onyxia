---
name: argo-mlops
description: Industrialiser un modèle sur Onyxia avec Argo Workflows (entraînement parallèle / recherche d'hyperparamètres distribuée sur Kubernetes) et ArgoCD (déploiement continu en GitOps). À charger pour paralléliser des entraînements, packager un modèle, écrire un Workflow Argo, déployer une API de prédiction ou mettre un modèle en production.
license: MIT
---

# MLOps sur Onyxia : Argo Workflows + ArgoCD

Pile recommandée :
**MLflow** (suivi/registre) + **Argo Workflows** (orchestration parallèle K8s) +
**ArgoCD** (déploiement GitOps). Chaque étape d'un workflow = un conteneur isolé
→ reproductibilité maximale.

## 1. Paralléliser une recherche d'hyperparamètres (Argo Workflows)
On crée des processus indépendants, un par combinaison d'hyperparamètres, chacun
entraîne le modèle puis logge dans MLflow. Squelette `withItems` :

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: hp-search-
spec:
  entrypoint: grid
  arguments:
    parameters:
      - name: experiment
        value: "mon-projet"
  templates:
    - name: grid
      steps:
        - - name: train
            template: train
            arguments:
              parameters: [{name: max_depth, value: "{{item.max_depth}}"},
                           {name: lr, value: "{{item.lr}}"}]
            withItems:
              - { max_depth: "4",  lr: "0.1" }
              - { max_depth: "8",  lr: "0.1" }
              - { max_depth: "8",  lr: "0.05" }
              - { max_depth: "12", lr: "0.05" }
    - name: train
      inputs:
        parameters: [{name: max_depth}, {name: lr}]
      container:
        image: inseefrlab/<image-projet>:main      # image contenant le code + deps
        command: ["python", "train.py"]
        args: ["--max-depth", "{{inputs.parameters.max_depth}}",
               "--lr", "{{inputs.parameters.lr}}",
               "--experiment", "{{workflow.parameters.experiment}}"]
        env:
          # URL auto-générée du service MLflow du catalogue (= $MLFLOW_TRACKING_URI)
          - { name: MLFLOW_TRACKING_URI, value: "https://user-<namespace>-<id>.user.lab.sspcloud.fr" }
          # les secrets S3/MLflow proviennent d'un Secret monté, pas du YAML en clair
```
Lancer / suivre :
```bash
argo submit workflow.yml --watch      # soumettre et suivre l'exécution
argo list                             # workflows en cours / terminés
argo logs @latest -f                  # logs du dernier workflow
# alternative sans CLI argo : kubectl create -f workflow.yml
# (create, pas apply : `generateName` est incompatible avec apply)
```
Chaque conteneur logge son run dans MLflow ; on compare ensuite les runs dans l'UI.

## 2. Packager le code d'entraînement
- Un script paramétré (`train.py` / `train.R`) qui lit ses données sur S3
  (skill `onyxia-storage-s3`) et logge dans MLflow (skill `mlflow-tracking`).
- Un `Dockerfile` partant d'une image de base Insee (ex. `inseefrlab/python-datascience`).
  L'image est (re)construite par CI (GitHub Actions) et publiée.
- Le workflow Argo référence cette image → environnement figé et rejouable.

## 3. Servir le modèle (API) et déployer en GitOps avec ArgoCD
Manifeste de déploiement (extrait), versionné dans le dépôt :
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: codification-api }
spec:
  template:
    spec:
      containers:
        - name: api
          image: inseefrlab/<image-api>:main
          imagePullPolicy: Always
          env:
            - { name: MLFLOW_TRACKING_URI, value: "https://user-<namespace>-<id>.user.lab.sspcloud.fr" }
            - { name: MLFLOW_MODEL_NAME,   value: "mon_modele" }
            - { name: MLFLOW_MODEL_VERSION, value: "1" }
```
+ un `Ingress` exposant l'API en `https://<prenom>-<nom>-api.lab.sspcloud.fr` :
hostname **choisi librement** sous le wildcard `*.lab.sspcloud.fr` (Ingress
custom), à distinguer des URLs auto-générées `user-<namespace>-<id>.user.lab.sspcloud.fr`
des services du catalogue.

GitOps : on commite/pousse les manifestes ; **ArgoCD** synchronise automatiquement
le cluster sur l'état du dépôt (sync auto en ~5 min ou sync forcée). L'API charge
sa version de modèle depuis le registre MLflow au démarrage.

## 4. Au-delà : maintien en condition opérationnelle
- Logs métier exposés par l'API → pipeline ETL planifié (un **`CronWorkflow`**
  Argo : même spec qu'un `Workflow` + champ `schedule` cron) qui les stocke en
  Parquet sur S3.
- Tableau de bord (Quarto Dashboards, Grafana, Superset) pour suivre l'usage et
  détecter une dérive des données / de la performance.
- Itérer : nouvelle version de modèle → nouvelle version d'image → ArgoCD redéploie,
  rollback possible en repointant une version antérieure.

## Garde-fous
- Jamais de secret en clair dans un YAML : utiliser des `Secret` K8s / Vault.
- Conteneur minimal par étape (uniquement le nécessaire) = reproductibilité.
- Toujours tracer : commit Git, données (chemin S3 + hash), run MLflow, version déployée.
