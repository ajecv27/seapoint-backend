"""Verified, full-resolution Caribbean geometry packaged for the hosted router."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct

import shapely

try:
    import seapoint_coast_data
    DIRECTORY = Path(seapoint_coast_data.__file__).parent
except ImportError:
    DIRECTORY = Path(__file__).with_name('data')  # Local data-build/test workspace.
COVERAGE = (-94.0, 5.0, -55.0, 34.0)
MAX_EXPANDED_BYTES = 128 * 1024 * 1024


def load_coast(directory=None):
    directory = Path(directory or DIRECTORY)
    manifest = json.loads((directory / 'manifest.json').read_text())
    if (manifest.get('format') != 'SPCOAST1' or manifest.get('crs') != 'EPSG:4326' or
            manifest.get('bounds') != list(COVERAGE) or
            not 0 < manifest.get('uncompressed_bytes', 0) <= MAX_EXPANDED_BYTES):
        raise ValueError('Invalid coastline manifest')
    path = directory / 'caribbean-v1.bin.gz'
    if path.stat().st_size != manifest['compressed_bytes'] or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Invalid coastline package size')
    compressed = path.read_bytes()
    if hashlib.sha256(compressed).hexdigest() != manifest['sha256']:
        raise ValueError('Coastline package checksum differs')
    from io import BytesIO
    with gzip.GzipFile(fileobj=BytesIO(compressed)) as stream:
        data = stream.read(MAX_EXPANDED_BYTES + 1)
    if (len(data) != manifest['uncompressed_bytes'] or
            hashlib.sha256(data).hexdigest() != manifest['uncompressed_sha256'] or
            data[:9] != b'SPCOAST1\n'):
        raise ValueError('Invalid coastline content')
    if len(data) < 13:
        raise ValueError('Truncated coastline header')
    count = struct.unpack_from('<I', data, 9)[0]
    if not 100 <= count <= 100000:
        raise ValueError('Unexpected coastline feature count')
    geometries, osm = [], []
    counts = [0, 0]
    offset = 13
    for _ in range(count):
        if offset + 5 > len(data):
            raise ValueError('Truncated coastline record')
        group, length = struct.unpack_from('<BI', data, offset)
        offset += 5
        if group not in (0, 1) or not 21 <= length <= 32 * 1024 * 1024 or offset + length > len(data):
            raise ValueError('Invalid coastline record')
        geometry = shapely.from_wkb(data[offset:offset + length])
        offset += length
        if (geometry.geom_type not in ('Polygon', 'MultiPolygon') or geometry.is_empty or
                not geometry.is_valid or geometry.area <= 0 or
                not all(math.isfinite(n) for n in geometry.bounds)):
            raise ValueError('Invalid coastline geometry')
        west, south, east, north = geometry.bounds
        if west < COVERAGE[0] - 1e-7 or south < COVERAGE[1] - 1e-7 or east > COVERAGE[2] + 1e-7 or north > COVERAGE[3] + 1e-7:
            raise ValueError('Coastline exceeds declared coverage')
        geometries.append(geometry)
        counts[group] += 1
        if group == 1:
            osm.append(geometry)
    expected = [s['features'] for s in manifest['sources']]
    if offset != len(data) or counts != expected or min(counts) < 100:
        raise ValueError('Incomplete coastline coverage')
    return geometries, osm, manifest


def select_routing_coast(gshhg, osm, manifest=None):
    """Use current detailed OSM coastlines for matched landmasses.

    Unioning both releases fills dredged harbours and shifts shorelines back
    to the older GSHHG outline. Retain GSHHG features with no intersecting OSM
    landmass so isolated islands absent from OSM still obstruct a route. This
    is one regional source policy, not a hand-drawn harbour exception.
    """
    from shapely.strtree import STRtree
    if not osm:
        raise ValueError('Detailed coastline data is missing')
    if manifest is not None:
        # The source matching is a build step, not recurring cold-start work.
        # Validate this tiny index against the immutable, already verified data.
        from . import COASTLINE_POLICY
        raw = Path(__file__).with_name('coast_policy.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != 'b8a09a0c60fdda3db51f9af88c6b1c36ed753f4632284eb29a5a3ca4fe5e01c9':
            raise ValueError('Coastline policy index checksum differs')
        policy = json.loads(raw)
        indices = policy['fallback_indices']
        if (policy['policy'] != COASTLINE_POLICY or policy['dataset'] != manifest['id'] or
                policy['coast_sha256'] != manifest['sha256'] or
                policy['gshhg_features'] != len(gshhg) or policy['osm_features'] != len(osm) or
                not isinstance(indices, list) or
                any(type(i) is not int or not 0 <= i < len(gshhg) for i in indices) or
                indices != sorted(set(indices))):
            raise ValueError('Coastline policy index does not match this dataset')
        return list(osm) + [gshhg[i] for i in indices]
    detailed = STRtree(osm)
    # Do not prepare every polygon here: preparing the full continental coast
    # creates large spatial indexes. Runtime prepares only encountered features.
    fallback = [g for g in gshhg if not any(
        g.intersects(detailed.geometries[int(i)]) for i in detailed.query(g))]
    return list(osm) + fallback
