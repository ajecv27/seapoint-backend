"""Test-only IPC fixture. Production always runs marine_routing.worker."""
import json
import sys
import time
from marine_routing import COASTLINE_POLICY

mode = sys.argv[1]
if mode == 'slow-start':
    time.sleep(5)
print(json.dumps({'type': 'ready', 'dataset': 'caribbean-osm-gshhg-20261114-v1', 'build': 'test-only', 'coastline_policy': COASTLINE_POLICY}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    if mode == 'slow':
        time.sleep(1)
    if mode == 'hung':
        time.sleep(5)
    if mode == 'crash':
        sys.exit(1)
    start, finish = request['start'], request['finish']
    body = {'status': 'ok', 'coastline_policy': COASTLINE_POLICY, 'coastline_dataset': 'caribbean-osm-gshhg-20261114-v1',
            'points': [{'lon':p[0], 'lat':p[1]} for p in (start, finish)]}
    print(json.dumps({'id':request['id'], 'status':200, 'body':body}), flush=True)
