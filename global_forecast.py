"""Immutable global GFS XYZ tiles for static forecast delivery.

Tiles retain the source model time and rate units. Higher zooms are sampled
for display; they add no meteorological resolution to the 0.25-degree grid.
"""
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np
from PIL import Image
from forecast_maps import HOST, decode_gfs, precipitation_range, read_url, rgba, sample_rates

BOUNDS = [[-85.0511287798066, -180.0], [85.0511287798066, 180.0]]
TILE_SIZE = 256
MAX_ZOOM = 4
STYLE = 'g1'


class CachedGFSReader:
    """Share the same immutable public GRIB record with both forecast renders."""
    def __init__(self, directory, reader=read_url):
        self.directory = Path(directory)
        self.reader = reader

    def __call__(self, url, byte_range=None):
        key = hashlib.sha256((url+repr(byte_range)).encode()).hexdigest()
        path = self.directory/(key+'.record')
        checksum = path.with_suffix('.sha256')
        try:
            data = path.read_bytes()
            if len(data)<=4_000_000 and hashlib.sha256(data).hexdigest()==checksum.read_text():
                return data
        except OSError:
            pass
        data = self.reader(url, byte_range)
        if not isinstance(data,bytes) or not 0<len(data)<=4_000_000:
            raise ValueError('Unexpected GFS record')
        self.directory.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp');temp.write_bytes(data);temp.replace(path)
        checksum.write_text(hashlib.sha256(data).hexdigest())
        return data

    def prune(self, now):
        if not self.directory.exists():return
        for path in self.directory.glob('*'):
            if path.is_file()and now-path.stat().st_mtime>2*86400:path.unlink()


def world_image(values, max_zoom=MAX_ZOOM):
    """Pixel-centred Web Mercator sampling, including longitude seam wrapping."""
    side=TILE_SIZE*(2**max_zoom)
    x=((np.arange(side)+.5)/side*360-180)%360/.25
    pixels=np.empty((side,side,4),dtype=np.uint8)
    for start in range(0,side,256):
        mercator=np.pi*(1-2*(np.arange(start,min(side,start+256))+.5)/side)
        latitudes=np.degrees(np.arctan(np.sinh(mercator)))
        y=(90-latitudes)/.25
        pixels[start:start+len(y)]=rgba(sample_rates(values,x,y)*3600)
    return Image.fromarray(pixels)


def tile_bytes(image):
    # A local palette bounds download/storage size while retaining transparent
    # rain edges. The map is a colour display, not a numeric rain-rate endpoint.
    quantized=image.quantize(colors=256,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE)
    output=BytesIO();quantized.save(output,format='PNG',optimize=True)
    return output.getvalue()


class WorldTiles:
    def __init__(self, directory, reader=None, max_zoom=MAX_ZOOM):
        if type(max_zoom)is not int or not 0<=max_zoom<=MAX_ZOOM:raise ValueError('Invalid tile zoom')
        self.directory=Path(directory)
        self.reader=reader or read_url
        self.max_zoom=max_zoom

    @staticmethod
    def _valid_tile(data):
        try:
            if not isinstance(data,bytes)or not 0<len(data)<=500_000:return False
            with Image.open(BytesIO(data))as image:
                if image.format!='PNG'or image.size!=(TILE_SIZE,TILE_SIZE):return False
                image.verify()
            with Image.open(BytesIO(data))as image:image.load()
            return True
        except (OSError,ValueError,SyntaxError,Image.DecompressionBombError):return False

    def _reuse(self, directory, run, stamp):
        try:
            raw=(directory/'ready.json').read_bytes()
            if len(raw)>65_536:return False
            ready=json.loads(raw)
            if not isinstance(ready,dict)or not isinstance(ready.get('tiles'),dict):return False
            expected={(f'{z}/{x}/{y}.png')for z in range(self.max_zoom+1)for x in range(2**z)for y in range(2**z)}
            if ready.get('model_run')!=run or ready.get('time')!=stamp or ready.get('max_zoom')!=self.max_zoom or set(ready['tiles'])!=expected:return False
            for name,digest in ready['tiles'].items():
                data=(directory/name).read_bytes()
                if hashlib.sha256(data).hexdigest()!=digest or not self._valid_tile(data):return False
            return True
        except (OSError,ValueError,KeyError,TypeError):return False

    def frame(self, run, stamp):
        cycle=datetime.fromtimestamp(run,timezone.utc)
        hour,remainder=divmod(stamp-run,3600)
        if remainder or not 1<=hour<=120:raise ValueError('Invalid global forecast hour')
        name=f'{cycle:%Y%m%d%H}-{hour:03d}-{STYLE}'
        final=self.directory/name
        if not self._reuse(final,run,stamp):
            stage=self.directory/('.building-'+name)
            if stage.exists():shutil.rmtree(stage)
            stage.mkdir(parents=True)
            try:
                base=f'{HOST}/gfs.{cycle:%Y%m%d}/{cycle:%H}/atmos/gfs.t{cycle:%H}z.pgrb2.0p25.f{hour:03d}'
                index=self.reader(base+'.idx').decode('utf-8')
                values=decode_gfs(self.reader(base,precipitation_range(index)),stamp)
                image=world_image(values,self.max_zoom)
                digests={}
                for z in range(self.max_zoom,-1,-1):
                    size=TILE_SIZE*(2**z)
                    level=image if z==self.max_zoom else image.resize((size,size),Image.Resampling.BILINEAR)
                    for x in range(2**z):
                        (stage/str(z)/str(x)).mkdir(parents=True,exist_ok=True)
                        for y in range(2**z):
                            path=f'{z}/{x}/{y}.png'
                            data=tile_bytes(level.crop((x*TILE_SIZE,y*TILE_SIZE,(x+1)*TILE_SIZE,(y+1)*TILE_SIZE)))
                            if not self._valid_tile(data):raise ValueError('Invalid global rain tile')
                            (stage/path).write_bytes(data);digests[path]=hashlib.sha256(data).hexdigest()
                (stage/'ready.json').write_text(json.dumps({'model_run':run,'time':stamp,'max_zoom':self.max_zoom,'tiles':digests},separators=(',',':')))
                if final.exists():shutil.rmtree(final)
                stage.rename(final)
            finally:
                if stage.exists():shutil.rmtree(stage)
        return {'time':stamp,'url_template':f'data/world/{name}/{{z}}/{{x}}/{{y}}.png',
                'model_run':run,'source':'NOAA GFS','resolution_km':28,'units':'mm/h',
                'period_seconds':0,'value_semantics':'instantaneous_rate',
                'bounds':BOUNDS,'tile_size':TILE_SIZE,'max_zoom':self.max_zoom}

    def prepare(self, snapshot, now):
        from forecast_service import RegionalForecastMaps
        frames=RegionalForecastMaps._frames(snapshot,'noaa-gfs',now,54)
        if (not frames or frames[0]['time']>now or frames[-1]['time']<now+54*3600 or
            any(b['time']-a['time']!=3600 for a,b in zip(frames,frames[1:]))):
            raise ValueError('Global source does not provide complete buffered coverage')
        result=[]
        for frame in frames:
            result.append(dict(self.frame(frame['model_run'],frame['time']),fetched_at=snapshot['fetched_at']))
        return result

    def prune(self, now):
        for directory in self.directory.iterdir():
            if not directory.is_dir()or directory.name.startswith('.'):continue
            try:run=json.loads((directory/'ready.json').read_text())['model_run']
            except (OSError,ValueError,KeyError):continue
            if now-run>25*3600:shutil.rmtree(directory)
