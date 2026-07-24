---
name: geodata
description: Geospatial handling for French statistical work on Onyxia — GeoParquet (geometry + attributes in one file, streamed from S3), commune/IRIS geometries (geo.api.gouv.fr, IGN AdminExpress), CRS choice (Lambert-93 EPSG:2154 for metropolitan France, EPSG:4326 lon/lat, EPSG:3857 only for web tiles), and choropleths with geopandas rendered via Quarto. Load whenever a task involves maps, communes, geometries, shapefiles, spatial joins, or a .geojson/.gpkg/.shp file. (Mots-clés français : carte, communes, géométrie, fond de carte, projection, choroplèthe, jointure spatiale)
license: MIT
---

# Geospatial data on Onyxia

Geospatial work reuses the platform's normal data path: stream from S3, keep
one reproducible file format, and render maps inside a Quarto cell. Load
`onyxia-storage-s3` (streaming) and `quarto-publication` (rendering) alongside
this skill.

## Storage: GeoParquet, not a CSV+GeoJSON split

`gpd.read_parquet` / `gdf.to_parquet` keep geometry **and** attributes in a
single file, work on S3, and preserve dtypes. Never serialise geometry into a
plain pandas parquet (shapely objects are lost) and never split
attributes/geometry across two files.

```python
import geopandas as gpd

# Stream from S3 first (skill onyxia-storage-s3) — do not copy locally unless a
# tool truly needs a file on disk.
gdf = gpd.read_parquet("s3://<bucket>/diffusion/communes_59.parquet")
gdf.to_parquet("output/communes_59.parquet")   # GeoParquet, gitignored
```

## Geometries (authoritative sources)

- `https://geo.api.gouv.fr/communes?codeDepartement=59&format=geojson&geometry=contour`
- IGN AdminExpress — authoritative commune/department/region contours; fetch via
  the `insee-public-data` skill.

## CRS: choose deliberately

- **EPSG:2154 (Lambert-93)** — metropolitan France; use for areas/distances and
  for choropleths (`gdf.to_crs(2154)` before plotting).
- **EPSG:4326** — raw lon/lat as returned by most APIs.
- **EPSG:3857 (Web Mercator)** — only when overlaying web tiles; never for a
  statistical map of France (it distorts shape and area).

## Plotting a choropleth (in a Quarto cell)

Draw in a `{python}` cell and let Quarto capture the figure with `plt.show()`
(per `quarto-publication`) — no `savefig` + `![]()`, no `IPython.display.Image`.

```python
#| fig-cap: "Indicator by commune"
import matplotlib.pyplot as plt

ax = gdf.to_crs(2154).plot(          # reproject BEFORE plotting
    column="indicator", cmap="Reds", legend=True,
    edgecolor="white", linewidth=0.3, figsize=(10, 10),
)
ax.set_axis_off()
plt.show()
```

## References

- geopandas: https://geopandas.org
- IGN AdminExpress / geo.api.gouv.fr (see `insee-public-data`)
- Projections France: EPSG:2154 (Lambert-93), EPSG:4326, EPSG:3857
