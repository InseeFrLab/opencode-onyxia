---
name: vault-secrets-onyxia
description: Gérer les secrets (clés d'API, mots de passe, tokens) avec Vault sur Onyxia/SSP Cloud — onglet « Mes secrets », CLI vault kv, injection automatique des secrets comme variables d'environnement à la création d'un service, lecture côté Python/R. À charger dès qu'une tâche implique un secret, une clé d'API, un mot de passe, un token, un fichier .env, ou qu'un credential risque d'être écrit en dur dans le code.
license: MIT
---

# Gérer les secrets avec Vault sur Onyxia

Onyxia fournit un coffre-fort **Vault** par utilisateur, piloté depuis l'onglet
**« Mes secrets »** du datalab ou en CLI. C'est LE mécanisme pour éviter tout
credential en dur.

> **Règle d'or** : un secret ne se **commite** jamais, ne se **logge** jamais,
> ne s'écrit jamais dans un notebook, un YAML ou un rendu Quarto. Il arrive
> toujours par **variable d'environnement**.

## Variables d'environnement injectées
| Variable | Rôle |
|---|---|
| `VAULT_ADDR` | URL du serveur Vault |
| `VAULT_TOKEN` | jeton d'authentification (temporaire) |
| `VAULT_MOUNT` | point de montage KV (ex. `onyxia-kv`) |
| `VAULT_TOP_DIR` | dossier racine de vos secrets (= votre identifiant) |

## Créer / lire un secret

**Interface** : « Mes secrets » → nouveau secret → paires clé/valeur
(ex. secret `api-insee` avec les clés `CLIENT_ID`, `CLIENT_SECRET`).

**Terminal — CLI vault** :
```bash
vault kv list "$VAULT_MOUNT/$VAULT_TOP_DIR"                     # lister
vault kv get  "$VAULT_MOUNT/$VAULT_TOP_DIR/api-insee"           # lire
vault kv put  "$VAULT_MOUNT/$VAULT_TOP_DIR/api-insee" \
  CLIENT_ID="xxx" CLIENT_SECRET="yyy"                           # écrire
vault kv get -field=CLIENT_SECRET \
  "$VAULT_MOUNT/$VAULT_TOP_DIR/api-insee"                       # une seule clé
```

## Injecter un secret dans un service
À la création d'un service Onyxia : configuration → **Vault** → renseigner le
chemin du secret (ex. `api-insee`). Chaque clé du secret devient alors une
**variable d'environnement** du service (`CLIENT_ID`, `CLIENT_SECRET`, …).

## Lire en code (jamais la valeur en dur)
```python
import os
client_secret = os.environ["CLIENT_SECRET"]
```
```r
client_secret <- Sys.getenv("CLIENT_SECRET")
```
En dev local hors injection : un fichier `.env` **non commité** (listé dans
`.gitignore`, skill `git-workflow-ds`) chargé via `python-dotenv` / `dotenv` R.

## Diagnostic / erreurs fréquentes
- `403 permission denied` (Vault) → `VAULT_TOKEN` expiré : relancer un service
  (nouveau jeton) ou se ré-authentifier.
- `No value found at ...` → chemin erroné : vérifier `VAULT_MOUNT` et
  `VAULT_TOP_DIR` (`vault kv list` pour explorer).
- La variable n'apparaît pas dans le service → le chemin du secret n'a pas été
  renseigné à la création du service (l'injection n'est pas rétroactive).

## Si un secret a fuité (commité, loggé, publié)
1. **Révoquer / faire tourner** le secret immédiatement (la purge d'historique
   ne suffit jamais : considérer le secret comme compromis).
2. Purger l'historique Git si besoin (`git filter-repo`, skill `git-workflow-ds`).
3. Recréer le secret dans Vault et réinjecter.

## Références
- docs.sspcloud.fr (rubrique secrets)
- https://developer.hashicorp.com/vault/docs/commands/kv
