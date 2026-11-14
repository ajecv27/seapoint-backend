"""Package public, source-pinned coastline data without publishing to PyPI."""
import base64
import csv
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import zipfile

VERSION = '2026.11.14.1'
work = Path(os.environ.get('SEAPOINT_COAST_WORK', Path(__file__).resolve().parent/'cache'))
package = work/'package'
output = Path(os.environ.get('SEAPOINT_COAST_DIST', 'dist'))
output.mkdir(exist_ok=True)
name = f'seapoint_coast_data-{VERSION}'
files = {'seapoint_coast_data/__init__.py': b'"""Pinned public Caribbean coastline data for SeaPoint."""\n'}
for file in sorted(package.iterdir()):
    if file.is_file():
        files['seapoint_coast_data/'+file.name] = file.read_bytes()
files[name+'.dist-info/METADATA'] = (
    'Metadata-Version: 2.1\nName: seapoint-coast-data\nVersion: '+VERSION+'\n'
    'Summary: Full-resolution, clipped Caribbean OSM and GSHHG coastline data\n'
    'Requires-Python: >=3.10\n'
    'License: Data components are separately licensed under ODbL 1.0 and LGPL 3.0-or-later.\n'
    'Project-URL: Source, https://github.com/ajecv27/seapoint-backend/tree/main/coast_build\n\n'
    'OpenStreetMap data copyright OpenStreetMap contributors: https://www.openstreetmap.org/copyright\n'
    'GSHHG 2.3.7 data: https://www.soest.hawaii.edu/pwessel/gshhg/\n'
).encode()
files[name+'.dist-info/WHEEL'] = b'Wheel-Version: 1.0\nGenerator: SeaPoint coast builder\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
rows = []
for path, data in files.items():
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
    rows.append((path, 'sha256='+digest, str(len(data))))
rows.append((name+'.dist-info/RECORD', '', ''))
stream = StringIO()
csv.writer(stream, lineterminator='\n').writerows(rows)
files[name+'.dist-info/RECORD'] = stream.getvalue().encode()
wheel = output/(name+'-py3-none-any.whl')
with zipfile.ZipFile(wheel, 'w', compression=zipfile.ZIP_STORED) as archive:
    for path, data in files.items():
        info = zipfile.ZipInfo(path, (2026, 11, 14, 0, 0, 0))
        archive.writestr(info, data)
sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
(output/'SHA256SUMS').write_text(sha+'  '+wheel.name+'\n')
(output/'manifest.json').write_bytes((package/'manifest.json').read_bytes())
print(json.dumps({'wheel':str(wheel),'sha256':sha,'bytes':wheel.stat().st_size}))
