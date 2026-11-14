"""Regenerate the source-selection index from the installed pinned coast release.

Run from the repository root: python -m coast_build.policy_index
Then update the printed SHA256 in marine_routing/coast_data.py.
"""
from pathlib import Path
import hashlib
import json
from marine_routing import COASTLINE_POLICY
from marine_routing.coast_data import load_coast, select_routing_coast

land, osm, manifest = load_coast()
gshhg = land[:manifest['sources'][0]['features']]
selected = select_routing_coast(gshhg, osm)
lookup = {id(geometry): index for index, geometry in enumerate(gshhg)}
policy = {'policy': COASTLINE_POLICY, 'dataset': manifest['id'],
    'coast_sha256': manifest['sha256'], 'gshhg_features': len(gshhg),
    'osm_features': len(osm),
    'fallback_indices': [lookup[id(geometry)] for geometry in selected[len(osm):]]}
path = Path(__file__).resolve().parents[1]/'marine_routing/coast_policy.json'
path.write_bytes((json.dumps(policy, indent=2)+'\n').encode('utf-8'))
print('Index SHA256:', hashlib.sha256(path.read_bytes()).hexdigest())
