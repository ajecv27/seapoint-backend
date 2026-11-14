from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,hashlib,json,time
import os
root=Path(os.environ.get("SEAPOINT_COAST_WORK", Path(__file__).resolve().parent/"cache"));root.mkdir(parents=True,exist_ok=True)
sources=[('osm-land.zip','https://osmdata.openstreetmap.de/download/land-polygons-split-3857.zip',954027097,'a461f7ea79eecad1caf7042aecc09d290ffc7274ecd7032e03dbf934dd3b4968'),('gshhg.zip','https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-shp-2.3.7.zip',149157845,'8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41')]
def get(item):
 name,url,size,expected=item;target=root/name
 if target.exists() and target.stat().st_size==size and hashlib.sha256(target.read_bytes()).hexdigest()==expected:return name
 temp=target.with_suffix('.part');digest=hashlib.sha256();count=0;last=time.monotonic()
 with urllib.request.urlopen(url,timeout=60)as response,temp.open('wb')as out:
  modified=response.headers.get('Last-Modified')
  while block:=response.read(1024*1024):
   out.write(block);digest.update(block);count+=len(block)
   if time.monotonic()-last>15:
    print(name,round(count/size*100,1),'percent',flush=True);last=time.monotonic()
 if count!=size or digest.hexdigest()!=expected:raise ValueError(f'Changed or incomplete coastline source {name}')
 temp.rename(target)
 (root/(name+'.json')).write_text(json.dumps({'url':url,'bytes':count,'sha256':digest.hexdigest(),'last_modified':modified,'retrieved_at':int(time.time())},indent=2))
 print(name,'complete',count,digest.hexdigest(),flush=True)
 return name
with ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(get,sources))
