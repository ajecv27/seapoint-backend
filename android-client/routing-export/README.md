# Collect the existing routing code

Run the pinned `export-routing-code.ps1` command supplied in the SeaPoint chat
from the Android Studio project terminal while Docker Desktop is running. The
script creates a uniquely named `SeaPoint-Routing-Code-*.zip` in that folder.
Attach the ZIP in the private chat for source review before deployment.

The default selection is the four routing containers reported on the user's
laptop: `seapoint-clearance-test` (port 8083 in the handoff),
`seapoint-global-osm-test`, `seapoint-global-test`, and `seapoint-routing`.
The container name alone does not establish which algorithm is correct or
whether draft/depth checking is implemented. Review and test the collected code
before choosing the production version.

The collector reads selected Docker metadata to identify Python launch modules
and application directories. `docker cp` retrieves those files and referenced
local Python helpers, plus requirements/pyproject/Dockerfile where available.
It makes no directory copies, starts/stops no containers, executes no commands
inside containers, reads no Docker environment variables, and uploads nothing.
Raw launch arguments are not saved. It bounds each file to 1 MiB and collected
source to 20 MiB. A maximum of 25 Python files is considered per container.

The export describes coastline filenames and sizes without copying shapefiles,
credentials files or `.env` files. A read-only request may collect the local
FastAPI `/openapi.json` schema from the container's published port. It sends no
coordinates or API keys. Existing app and routing source files are unchanged.
Only a new local ZIP is created; temporary collection files are removed.

The generated ZIP is for private review. No collected routing source or local
data is automatically published to GitHub. The collector itself and synthetic
tests contain no private container code or coastline data.

Tests use simulated Docker responses for root/package launch modules, imported
helpers, absent containers, metadata filtering, coastline inventories, bounded
source copying and repeat exports. Windows CI runs the smoke check under both
Windows PowerShell 5.1 and PowerShell 7.
