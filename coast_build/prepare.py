from pathlib import Path
import zipfile,subprocess,json,gzip,struct,hashlib,time,shutil
import shapely
from shapely.geometry import shape,box
import os
root=Path(os.environ.get("SEAPOINT_COAST_WORK", Path(__file__).resolve().parent/"cache"))
out=root/"package";out.mkdir(parents=True,exist_ok=True)
bounds=(-94.0,5.0,-55.0,34.0)
fields=[]
for source,archive,match in [('gshhg','gshhg.zip','GSHHS_f_L1'),('osm','osm-land.zip','land_polygons')]:
 directory=root/source;directory.mkdir(exist_ok=True)
 with zipfile.ZipFile(root/archive)as z:
  for info in z.infolist():
   p=Path(info.filename)
   if p.stem==match and p.suffix.lower()in['.shp','.shx','.dbf','.prj','.qix','.cpg']:
    target=directory/p.name
    if not target.exists():
     with z.open(info)as src,target.open('wb')as dst:shutil.copyfileobj(src,dst,4*1024*1024)
  for info in z.infolist():
   if Path(info.filename).name.upper()in['LICENSE.TXT','COPYING.LESSERV3'] or (source=='osm' and Path(info.filename).name=='README.txt'):
    (out/(source+'-'+Path(info.filename).name)).write_bytes(z.read(info))
 sourcefile=next(directory.glob('*.shp'));target=root/(source+'-caribbean.geojson')
 if not target.exists():
  cmd=['ogr2ogr','-f','GeoJSON',str(target),str(sourcefile),'-spat',*[str(n)for n in bounds],'-spat_srs','EPSG:4326','-t_srs','EPSG:4326','-clipdst',*[str(n)for n in bounds],'-lco','COORDINATE_PRECISION=9']
  print('Extracting',source,flush=True)
  subprocess.run(cmd,check=True,timeout=240)
 raw=json.loads(target.read_text());polygons=[];invalid=[]
 for feature in raw['features']:
  if not feature.get('geometry'):continue
  geom=shape(feature['geometry'])
  if geom.is_empty or geom.area==0:continue
  if geom.geom_type=='GeometryCollection':parts=list(geom.geoms)
  else:parts=[geom]
  for g in parts:
   if g.geom_type not in['Polygon','MultiPolygon']or g.is_empty:continue
   if not g.is_valid:invalid.append((feature.get('id'),shapely.is_valid_reason(g)))
   polygons.append(g)
 print(source,'features',len(polygons),'invalid',invalid[:10],flush=True)
 if invalid:raise ValueError(f'Invalid coastline {source}: {len(invalid)}')
 fields.append((source,polygons,json.loads((root/(archive+'.json')).read_text())))
with (out/'caribbean-v1.bin').open('wb')as f:
 f.write(b'SPCOAST1\n');f.write(struct.pack('<I',sum(len(p)for s,p,m in fields)))
 for source,polygons,meta in fields:
  for geom in polygons:
   wkb=shapely.to_wkb(geom,output_dimension=2,byte_order=1)
   f.write(struct.pack('<BI',0 if source=='gshhg'else 1,len(wkb)));f.write(wkb)
raw=(out/'caribbean-v1.bin').read_bytes()
compressed=gzip.compress(raw,compresslevel=9,mtime=0)
(out/'caribbean-v1.bin.gz').write_bytes(compressed)
(out/'caribbean-v1.bin').unlink()
manifest={'id':'caribbean-osm-gshhg-20261114-v1','format':'SPCOAST1','crs':'EPSG:4326','bounds':list(bounds),'created_at':int(time.time()),'build_tools':{'shapely':shapely.__version__,'geos':shapely.geos_version_string,'gdal':subprocess.check_output(['ogr2ogr','--version'],text=True).strip()},'compressed_bytes':len(compressed),'uncompressed_bytes':len(raw),'sha256':hashlib.sha256(compressed).hexdigest(),'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'sources':[dict(source=source,features=len(p),**m)for source,p,m in fields],'precision':'Original full-resolution source geometry clipped to coverage; coordinates exported at 9 decimal places; no simplification.'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2),flush=True)
