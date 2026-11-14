# Pinned public routing coastline

This build prepares the two public coastline sources used by the existing
Caribbean routing prototype. It retains both GSHHG 2.3.7 full-resolution level-1
land and detailed OpenStreetMap land polygons inside 94 W–55 W, 5 N–34 N.
It clips to coverage without simplifying geometry. GDAL exports coordinates at
nine decimal places, and every polygon is checked for validity before packing.

The original archives are HTTPS downloads pinned by byte count and SHA-256.
The OSM source is the 2026-11-13T15:00:00Z snapshot distributed on 2026-11-14.
A source change fails the build instead of silently updating the dataset.
Source URLs, hashes, retrieval times, build-tool versions, feature counts, CRS,
coverage and packed-data checksums remain in `manifest.json`.

The binary stream has a versioned header and source-grouped WKB polygon records.
A pure-data Python wheel lets the existing Render `pip install -r requirements.txt`
install it during deployment, so phone requests do not download the world data
or require the laptop. The wheel is published as an immutable GitHub release
asset with `SHA256SUMS`, not uploaded to PyPI. The router pins the actual wheel
hash when it adopts the release. No user routes or private container data are
included.

OSM: copyright OpenStreetMap contributors, Open Database License 1.0. See the
bundled source README and https://www.openstreetmap.org/copyright.
GSHHG: GNU LGPL 3.0 or later; the original licence notice and LGPL text are
included. Source: https://www.soest.hawaii.edu/pwessel/gshhg/ .

The data describes mapped land. It provides no depths, reefs, channels,
restrictions, or assurance that a route is safe to navigate.
