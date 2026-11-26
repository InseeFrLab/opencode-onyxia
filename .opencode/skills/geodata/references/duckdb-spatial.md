# Spatial analysis in DuckDB (and Overture Maps on Onyxia)

> Adapted from the `spatial` skill references of [duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills)
> (MIT) — see `THIRD_PARTY.md`. Snippets tested on DuckDB 1.5.6 on an SSP Cloud service.
> For French official boundaries (communes, IRIS, AdminExpress) and choropleths use the main `geodata` skill;
> use this file for SQL-side spatial work on big data without loading it into geopandas.

## 1. Setup

```sql
INSTALL spatial; LOAD spatial;
SET geometry_always_xy = true;   -- ALWAYS set it: without it DuckDB warns and may use [lat, lon] axis order
-- H3 hexagonal binning (community extension):
INSTALL h3 FROM community; LOAD h3;
```

## 2. Read / write spatial data

| Format | Read | Notes |
|---|---|---|
| GeoParquet | `FROM 's3://<bucket>/x.parquet'` | native; the geometry column comes back as `GEOMETRY` |
| GeoJSON, Shapefile, GeoPackage, FlatGeobuf, KML, GPX | `FROM ST_Read('file.gpkg')` | GDAL, 50+ formats |
| CSV with coordinates | `SELECT *, ST_Point(lon, lat) AS geom FROM 'f.csv'` | order is **(lon, lat)** = (x, y) |
| OSM extract | `ST_ReadOSM('region.osm.pbf')` | tags as a `MAP` column |

```sql
-- write: GeoParquet is the project format (see `geodata`); GDAL drivers for exchange
COPY (SELECT * FROM t) TO 'out.gpkg' WITH (FORMAT GDAL, DRIVER 'GPKG');
COPY (SELECT * FROM t) TO 'out.geojson' WITH (FORMAT GDAL, DRIVER 'GeoJSON');
```

## 3. Coordinates and distances (France)

- Store/exchange in **EPSG:4326** (lon/lat); compute metric quantities in **Lambert-93 (EPSG:2154)** for
  metropolitan France: `ST_Transform(geom, 'EPSG:4326', 'EPSG:2154')` (with `geometry_always_xy = true`),
  after which `ST_Distance`, `ST_Area`, `ST_Buffer(geom, 500)` are in **metres**.
- Geodesic alternative without reprojection: `ST_Distance_Spheroid(a, b)` (metres) — **only accepts `POINT_2D`**:
  `ST_Point(ST_X(g), ST_Y(g))::POINT_2D`, or `ST_Point(lon, lat)::POINT_2D` directly.
- Never compare `ST_Distance` on lon/lat geometries with a distance in metres: it is in degrees.

## 4. Function cheat sheet

| Need | Functions |
|---|---|
| Build | `ST_Point(x, y)`, `ST_MakeEnvelope(xmin, ymin, xmax, ymax)`, `ST_GeomFromText(wkt)`, `ST_GeomFromGeoJSON(json)` |
| Relations | `ST_Contains(a, b)`, `ST_Within`, `ST_Intersects`, `ST_Covers`, `ST_Disjoint`, `ST_Touches`, `ST_DWithin(a, b, d)` |
| Measure | `ST_Area`, `ST_Length`, `ST_Perimeter`, `ST_Distance`, `ST_Distance_Spheroid`, `ST_Area_Spheroid` |
| Transform | `ST_Transform`, `ST_Centroid`, `ST_Buffer`, `ST_Simplify(g, tol)`, `ST_ConvexHull`, `ST_Union`, `ST_Intersection`, `ST_Difference` |
| Aggregate | `ST_Extent_Agg`, `ST_Union_Agg`, `ST_Collect` |
| Access | `ST_X`, `ST_Y`, `ST_GeometryType`, `ST_AsText`, `ST_AsGeoJSON` |
| Look up the rest | `FROM duckdb_functions() WHERE function_name ILIKE 'st\_%' ESCAPE '\'` (names are mixed-case: use `ILIKE`) |

## 5. Patterns

```sql
-- points inside polygons (spatial join) — filter with a cheap bbox test first on big tables
SELECT p.id, z.code
FROM points p JOIN zones z ON ST_Within(p.geom, z.geom);

-- nearest 3 targets per row, in metres
SELECT a.id, b.id AS nearest,
       ST_Distance_Spheroid(a.geom::POINT_2D, b.geom::POINT_2D) AS dist_m
FROM locations a
CROSS JOIN LATERAL (
    SELECT id, geom FROM targets t
    ORDER BY ST_Distance_Spheroid(a.geom::POINT_2D, t.geom::POINT_2D) LIMIT 3
) b;

-- density per H3 hexagon (resolution 7 ≈ 1.2 km edge; 9 ≈ 174 m; 5 ≈ 8 km)
SELECT h3_latlng_to_cell(lat, lon, 7) AS hex, count() AS n
FROM points GROUP BY hex ORDER BY n DESC;   -- h3_cell_to_boundary_wkt(hex) gives the polygon to map
```

## 6. Overture Maps (free global GeoParquet on AWS S3)

Places (POIs), buildings, roads, admin divisions, addresses. Useful for context data; it is OSM/third-party
derived — **for official French statistics use IGN/INSEE sources** (`geodata`, `insee-public-data`).

**Two traps on Onyxia (both verified):**
1. Your environment sets `AWS_ACCESS_KEY_ID`/`AWS_ENDPOINT_URL` for **MinIO**. An S3 secret for the AWS bucket
   must therefore be **scoped to that bucket and use empty keys** (anonymous). An unscoped region secret, or a
   `PROVIDER config` secret without empty keys, sends your MinIO key to AWS (`InvalidAccessKeyId`) and/or
   shadows your MinIO secret.
2. The `aws` CLI is also pointed at MinIO: pass the AWS endpoint explicitly.

```sql
LOAD httpfs;
CREATE OR REPLACE SECRET overture (TYPE S3, KEY_ID '', SECRET '', REGION 'us-west-2',
                                   SCOPE 's3://overturemaps-us-west-2');
-- the MinIO secret keeps serving your own bucket: check with
SELECT name FROM which_secret('s3://overturemaps-us-west-2/release/x', 's3');   -- overture
```

```bash
# latest release (the CLI needs the explicit AWS endpoint because AWS_ENDPOINT_URL points to MinIO)
aws --no-sign-request --region us-west-2 --endpoint-url https://s3.us-west-2.amazonaws.com \
    s3 ls s3://overturemaps-us-west-2/release/
```

Do not hard-code a release: read it from that listing (e.g. `2026-11-18.0`) and parameterise it.
**Schemas change between releases** (e.g. places `categories` was replaced by `taxonomy` / `basic_category`):
`DESCRIBE` the theme before writing a query, and list real category values with a small bbox
`GROUP BY basic_category` instead of guessing them.
Needs outbound access to AWS S3 (us-west-2); if it is blocked, say so instead of retrying.

Layout: `s3://overturemaps-us-west-2/release/<RELEASE>/theme=<theme>/type=<type>/*`

| Theme / type | Content | Useful columns |
|---|---|---|
| `places/place` | POIs | `names.primary`, `basic_category`, `taxonomy.primary`, `confidence`, `addresses` |
| `buildings/building` | footprints | `height`, `num_floors`, `class` |
| `divisions/division`, `division_area` | admin points / polygons | `subtype`, `country`, `population` |
| `transportation/segment` | road/rail centrelines | `class`, `subtype`, `names.primary` |
| `addresses/address` | addresses | — |

**Always filter on the `bbox.*` columns first** (partition pruning; this is what keeps a query to seconds instead of
scanning the planet):

```sql
SET geometry_always_xy = true;
SELECT names.primary AS name, basic_category, confidence,
       round(ST_Distance_Spheroid(ST_Point(ST_X(geometry), ST_Y(geometry))::POINT_2D,
                                  ST_Point(2.3522, 48.8566)::POINT_2D)) AS dist_m
FROM read_parquet('s3://overturemaps-us-west-2/release/<RELEASE>/theme=places/type=place/*')
WHERE bbox.xmin BETWEEN 2.33 AND 2.37 AND bbox.ymin BETWEEN 48.84 AND 48.87   -- bbox first
  AND basic_category = 'hospital' AND confidence > 0.7
ORDER BY dist_m LIMIT 10;
```

POI categories and positions are crowd/AI-derived and sometimes wrong (a car park tagged `hospital` came back with
`confidence` 0.98): never trust `confidence` alone, sanity-check names and positions. Bound every Overture query (bbox + `LIMIT`/aggregation, see `eda-duckdb/references/safe-query.md`): a missing
bbox filter scans billions of rows.
