---
name: onyxia-storage-s3
description: Lire et écrire des données sur le stockage S3/MinIO d'Onyxia (SSP Cloud), en Python (s3fs, pyarrow, duckdb, pandas/polars), en R (arrow, aws.s3) et via la CLI aws s3. À charger dès qu'une tâche lit ou écrit des données, mentionne S3, MinIO, un bucket, du Parquet/CSV distant, le dossier diffusion, ou une erreur 403 sur le stockage.
license: MIT
---

# Accès au stockage S3/MinIO sur Onyxia

Le datalab utilise **MinIO** (API compatible S3). Les identifiants sont injectés
automatiquement dans le service à sa création — **ne jamais les coder en dur**.
Endpoint MinIO du SSP Cloud : `https://minio.lab.sspcloud.fr`.

> **Règle d'or Onyxia** : ne pas télécharger les fichiers dans le conteneur,
> **ingérer directement la donnée en mémoire** depuis S3 (via `s3fs`, `arrow`,
> `duckdb`). On ne copie en local (`aws s3 cp`) que si un outil exige vraiment
> un fichier sur disque.

## Variables d'environnement injectées
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
- `AWS_DEFAULT_REGION`, `AWS_S3_ENDPOINT` (hôte seul, ex. `minio.lab.sspcloud.fr`)

Bucket personnel = nom d'utilisateur SSP Cloud. Le dossier `diffusion/` à la
racine d'un bucket est **lisible par tous les utilisateurs authentifiés**
(mécanisme de partage / collaboration / reproductibilité). Jeton valide **7 jours**.

## Python — s3fs (lecture/écriture en mémoire, recommandé)
```python
import os, s3fs, pandas as pd

fs = s3fs.S3FileSystem(
    client_kwargs={"endpoint_url": f"https://{os.environ['AWS_S3_ENDPOINT']}"}
)
BUCKET = os.environ["USERNAME"]

fs.ls(f"{BUCKET}/diffusion")                     # lister

# Lire / écrire un DataFrame (CSV : 'r'/'w' ; Parquet binaire : 'rb'/'wb')
with fs.open(f"{BUCKET}/diffusion/df.parquet", "rb") as f:
    df = pd.read_parquet(f)
with fs.open(f"{BUCKET}/diffusion/out.parquet", "wb") as f:
    df.to_parquet(f)

# Transférer des fichiers locaux <-> S3 (ex. ShapeFile multi-fichiers)
fs.put("dossier_local/", f"{BUCKET}/diffusion/dossier/", recursive=True)
fs.get(f"{BUCKET}/diffusion/dossier/", "dossier_local/", recursive=True)
fs.glob(f"{BUCKET}/diffusion/dossier/**/COMMUNE.*")
```

## Python — duckdb (gros volumes, lecture paresseuse)
Privilégier ces outils sur du Parquet : lecture colonne, *predicate pushdown*,
seules les données utiles remontent en mémoire.

```python
import duckdb
con = duckdb.connect()
con.sql("INSTALL httpfs; LOAD httpfs;")
con.sql(f"SET s3_endpoint='{os.environ['AWS_S3_ENDPOINT']}'; SET s3_use_ssl=true;")
con.sql(f"""
  FROM read_parquet('s3://{BUCKET}/data/RPindividus.parquet')
  SELECT AGED, DEPT, SUM(IPONDI) AS n WHERE DEPT IN ('11','31','34') GROUP BY AGED, DEPT
""").to_df()
```

## R — duckdb (recommandé pour Parquet sur S3)
DuckDB lit/écrit le Parquet sur MinIO via l'extension `httpfs`, avec lecture
paresseuse et *predicate pushdown*. On configure l'accès S3 à partir des
variables d'environnement injectées (via le *secrets manager* de DuckDB).

```r
library(duckdb); library(DBI); library(dplyr)
 
con <- dbConnect(duckdb::duckdb())
dbExecute(con, "INSTALL httpfs; LOAD httpfs;")
 
# Accès MinIO depuis les variables AWS_* (path-style + SSL obligatoires)
dbExecute(con, sprintf("
  CREATE OR REPLACE SECRET minio (
    TYPE s3, KEY_ID '%s', SECRET '%s', SESSION_TOKEN '%s',
    ENDPOINT '%s', USE_SSL true, URL_STYLE 'path'
  );",
  Sys.getenv("AWS_ACCESS_KEY_ID"), Sys.getenv("AWS_SECRET_ACCESS_KEY"),
  Sys.getenv("AWS_SESSION_TOKEN"), Sys.getenv("AWS_S3_ENDPOINT")))
 
BUCKET <- Sys.getenv("USERNAME")
 
# 1) Requête SQL directe
df <- dbGetQuery(con, sprintf("
  SELECT AGED, DEPT, SUM(IPONDI) AS n
  FROM read_parquet('s3://%s/data/RPindividus.parquet')
  WHERE DEPT IN ('18','28','36')
  GROUP BY AGED, DEPT", BUCKET))
 
# 2) Style dplyr (lecture paresseuse) via une vue sur le dataset partitionné
dbExecute(con, sprintf("CREATE VIEW rp AS
  SELECT * FROM read_parquet('s3://%s/data/RPindividus_partitionne/**/*.parquet',
                             hive_partitioning = true);", BUCKET))
res <- tbl(con, "rp") |>
  filter(DEPT %in% c("18", "28", "36")) |>
  group_by(AGED, DEPT) |> summarise(n = sum(IPONDI), .groups = "drop") |>
  collect()
 
# Écriture sur S3
dbExecute(con, sprintf("COPY (SELECT * FROM rp) TO 's3://%s/diffusion/out.parquet'
                        (FORMAT parquet);", BUCKET))
 
dbDisconnect(con, shutdown = TRUE)
```
 
## R — aws.s3 (alternative, fichiers CSV/divers)
```r
library(aws.s3)
bucket <- Sys.getenv("USERNAME")
df <- s3read_using(readr::read_csv, object = "data/t.csv", bucket = bucket, opts = list(region = ""))
s3write_using(df, arrow::write_parquet, object = "out/t.parquet", bucket = bucket, opts = list(region = ""))
```

## Terminal — aws s3 (CLI préférée à mc)
La CLI `aws` lit les variables AWS_* automatiquement ; préciser l'endpoint MinIO.
```bash
aws --endpoint-url "https://$AWS_S3_ENDPOINT" s3 ls "s3://$USERNAME/diffusion/"
aws --endpoint-url "https://$AWS_S3_ENDPOINT" s3 cp ./fichier.parquet "s3://$USERNAME/data/"
aws --endpoint-url "https://$AWS_S3_ENDPOINT" s3 sync ./local_dir "s3://$USERNAME/data/dir"
```
Astuce : exporter `AWS_ENDPOINT_URL="https://$AWS_S3_ENDPOINT"` une fois pour
éviter de répéter `--endpoint-url`. (Le client `mc`, alias `s3`, existe aussi
sur la plateforme mais on privilégie `aws s3`.)

## Diagnostic
- **403 / AccessDenied** → jeton expiré (7 j). Sauvegarder code/données et
  repartir d'un nouveau service (jeton frais) ; c'est la cause la plus fréquente.
- **Endpoint** : toujours `https://$AWS_S3_ENDPOINT`. Une URL sans schéma échoue.
- **region** : avec MinIO, `region = ""` (R) évite les résolutions AWS parasites.

## Partage / collaboration
Déposer dans `s3://<bucket>/diffusion/` rend lisible par tous. Pour un projet
collaboratif, s'accorder sur le bucket d'un membre et y mettre les données dans
`diffusion/` ; le code de production reste, lui, sur Git.

## Références
- docs.sspcloud.fr/content/storage.html
- « Python pour la data science » (L. Galiana), chap. Parquet & cloud :
  pythonds.linogaliana.fr/content/manipulation/05_parquet_s3.html
