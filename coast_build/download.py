from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,hashlib,json,time,subprocess
import os
root=Path(os.environ.get("SEAPOINT_COAST_WORK", Path(__file__).resolve().parent/"cache"));root.mkdir(parents=True,exist_ok=True)
sources=[('osm-land.zip','https://osmdata.openstreetmap.de/download/land-polygons-split-3857.zip',954027097,'a461f7ea79eecad1caf7042aecc09d290ffc7274ecd7032e03dbf934dd3b4968'),('gshhg.zip','https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-shp-2.3.7.zip',149157845,'8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41')]
def get(item):
 name,url,size,expected=item;target=root/name
 if target.exists() and target.stat().st_size==size and hashlib.sha256(target.read_bytes()).hexdigest()==expected:return name
 temp=target.with_suffix('.part');headers=target.with_suffix('.headers')
 print('Downloading',name,'from',url,flush=True)
 subprocess.run(['curl','--ipv4','--fail','--location','--retry','3','--retry-delay','3',
                 '--connect-timeout','20','--max-time','600','--dump-header',str(headers),
                 '--output',str(temp),url],check=True)
 digest=hashlib.sha256();count=0
 with temp.open('rb')as stream:
  while block:=stream.read(1024*1024):digest.update(block);count+=len(block)
 modified=None
 for line in headers.read_text(errors='replace').splitlines():
  if line.lower().startswith('last-modified:'):modified=line.split(':',1)[1].strip()
 if count!=size or digest.hexdigest()!=expected:raise ValueError(f'Changed or incomplete coastline source {name}')
 temp.rename(target)
 (root/(name+'.json')).write_text(json.dumps({'url':url,'bytes':count,'sha256':digest.hexdigest(),'last_modified':modified,'retrieved_at':int(time.time())},indent=2))
 print(name,'complete',count,digest.hexdigest(),flush=True)
 return name
with ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(get,sources))
