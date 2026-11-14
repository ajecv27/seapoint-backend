"""Build an atomic static radar publication, independent of the Render service."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from radar_view import radar_page


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Radar template changed; static export needs review: ' + old[:70])
    return text.replace(old, new, 1)


def static_html():
    html = radar_page(17.12, -61.8, 'Antigua')
    old = 'const config=' + json.dumps(dict(lat=17.12, lon=-61.8, name='Antigua')) + ';'
    html = replace_once(html, old, """const params=new URLSearchParams(location.search);
const coordinate=(key,fallback,limit)=>{const raw=params.get(key);const value=Number(raw);return raw!==null&&raw.trim()!==''&&Number.isFinite(value)&&Math.abs(value)<=limit?value:fallback;};
const config={lat:coordinate('lat',17.12,85),lon:coordinate('lon',-61.8,180),name:(params.get('name')||'Antigua').slice(0,160)};""")
    vendors = json.loads((ROOT/'static_site/vendor.json').read_text())
    for name, entry in vendors.items():
        if entry['url'] in html:
            html = html.replace(entry['url'], 'vendor/'+name)
    html = replace_once(html, "style:'/basemap-style'", "style:'basemap-style.json'")
    html, count = re.subn(r'/rain-motion\.js\?v=\d+', 'rain-motion.js', html)
    if count != 1:
        raise ValueError('Expected one optional motion script')
    html = replace_once(html, "'/global-rain.js?v=2'", "'global-rain.js?v=2'")
    html = replace_once(html, "fetchWeatherJson('/radar-frames',30000);if(!response.ok||!Array.isArray(data.frames))throw new Error();",
        "fetchWeatherJson('https://api.rainviewer.com/public/weather-maps.json',15000);if(!response.ok||!Array.isArray(data.radar?.past))throw new Error();")
    html = replace_once(html, 'observed=data.frames.filter(', 'observed=data.radar.past.filter(')
    html = replace_once(html, "fetchWeatherJson('/forecast-frames',FORECAST_DEADLINE_MS)",
        "fetchWeatherJson('data/latest.json?v='+Math.floor(Date.now()/300000),15000)")
    old = '  const now=Date.now()/1000;\n  const validBounds='
    new = """  const now=Date.now()/1000;
  if(data.static_manifest_version!==1||!Number.isFinite(data.published_at)||data.published_at>now+300||now-data.published_at>86400||!Number.isFinite(data.available_until)||data.available_until<=now)throw new Error();
  data.forecast_until=Math.min(now+48*3600,data.available_until);
  data.coverage_complete=data.available_until>=now+48*3600;
  data.updating=false;
  const validBounds="""
    html = replace_once(html, old, new)
    old = "+' Antigua time.').join(' ');"
    new = "+' Antigua time.').join(' ')+(forecastMeta.published_at?' Data published '+format(forecastMeta.published_at)+' Antigua time.'+(Date.now()/1000-forecastMeta.published_at>3*3600?' Publication update delayed.':''):'');"
    html = replace_once(html, old, new)
    html = replace_once(html, '</section>\n<footer id="player"', '<p><a href="vendor/NOTICE.txt" target="_blank" rel="noopener">Map library licences</a></p></section>\n<footer id="player"')
    # No request needed by this page may point to the sleeping application server.
    for dependency in ["'/radar-frames'", "'/forecast-frames'", "'/basemap-style'", "'/rain-motion.js", "'/global-rain.js"]:
        if dependency in html:
            raise ValueError('Render dependency remains: '+dependency)
    return html


def vendor_assets(output):
    vendors = json.loads((ROOT/'static_site/vendor.json').read_text())
    for name, entry in vendors.items():
        path = output/'vendor'/name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']:
            continue
        with urlopen(entry['url'], timeout=30) as response:
            data = response.read(2_000_001)
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Vendor integrity check failed: '+name)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
    notices = []
    for name in ('leaflet-LICENSE','maplibre-LICENSE','binding-LICENSE'):
        notices.append(name+'\n'+(output/'vendor'/name).read_text())
    (output/'vendor/NOTICE.txt').write_text('\n\n'.join(notices))


def write_shell(output):
    output.mkdir(parents=True,exist_ok=True)
    vendor_assets(output)
    (output/'index.html').write_text(static_html())
    shutil.copy2(ROOT/'rain_motion.js', output/'rain-motion.js')
    shutil.copy2(ROOT/'global_rain.js', output/'global-rain.js')
    (output/'.nojekyll').write_text('')
    from basemap_service import basemap_document
    try:
        style = basemap_document()
        (output/'basemap-style.json').write_text(json.dumps(style,separators=(',',':')))
    except Exception:
        # A previously published real style remains useful during a provider outage.
        style=json.loads((output/'basemap-style.json').read_text())
    if style.get('version') != 8 or not style.get('sources') or not style.get('layers'):
        raise ValueError('No valid basemap style')


def publish_forecast(service, report, output, now, global_frames=None):
    """Copy and verify all images before switching the local latest pointer."""
    from forecast_service import RegionalForecastMaps
    if report.get('status') != 'ready':
        raise ValueError('Forecast is not ready')
    sources = {source['provider']: source for source in report.get('sources', [])}
    selected = {}
    for provider in ('noaa-gfs','arome-antilles'):
        source_frames = [f for f in report.get('frames',[]) if f.get('provider')==provider]
        if not source_frames:
            continue
        first = source_frames[0]
        snapshot = dict(status='ready',units='mm/h',model_run=first['model_run'],
                        fetched_at=sources.get(provider, {}).get('fetched_at', report['fetched_at']),resolution_km=first['resolution_km'],
                        bounds=first['bounds'],frames=source_frames)
        for frame in RegionalForecastMaps._frames(snapshot,provider,now,54):
            selected[frame['time']]=frame
    frames = sorted(selected.values(),key=lambda f:f['time'])
    if (not frames or frames[0]['time']>now or frames[-1]['time']<now+54*3600 or
            any(b['time']-a['time']!=3600 for a,b in zip(frames,frames[1:]))):
        raise ValueError('A complete buffered forecast is required for publication')
    world = {}
    if global_frames is not None:
        from global_forecast import BOUNDS, MAX_ZOOM, TILE_SIZE, STYLE
        for frame in global_frames:
            run=frame.get('model_run');stamp=frame.get('time');fetched=frame.get('fetched_at')
            if (type(run)is not int or run%21600 or not 0<=now-run<86400 or
                type(stamp)is not int or type(fetched)is not int or not run<=fetched<=now+60):
                raise ValueError('Invalid global forecast source times')
            hour,remainder=divmod(stamp-run,3600)
            cycle=datetime.fromtimestamp(run,timezone.utc).strftime('%Y%m%d%H')
            if (remainder or not 1<=hour<=120 or frame.get('max_zoom')!=MAX_ZOOM or
                frame.get('tile_size')!=TILE_SIZE or frame.get('bounds')!=BOUNDS or
                frame.get('units')!='mm/h' or
                frame.get('url_template')!=f'data/world/{cycle}-{hour:03d}-{STYLE}/{{z}}/{{x}}/{{y}}.png'):
                raise ValueError('Invalid global forecast tile identity')
            world[stamp]=frame
        if any(frame['time']not in world for frame in frames):
            raise ValueError('Global tiles missing for advertised forecast')
    generation = datetime.fromtimestamp(now,timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    final = output/'data/generations'/generation
    stage = output/'data/generations'/('.building-'+generation)
    stage.mkdir(parents=True,exist_ok=False)
    try:
        public = []
        for frame in frames:
            name=frame['url'].rsplit('/',1)[-1]
            data=service.image(name)
            from forecast_maps import ForecastMaps
            if not isinstance(data,bytes) or not ForecastMaps._valid_png(data):
                raise ValueError('An advertised forecast image is missing or corrupt: '+name)
            digest=hashlib.sha256(data).hexdigest()
            published_name=Path(name).stem+'-'+digest[:16]+'.png'
            (stage/published_name).write_bytes(data)
            entry=dict(frame,url=f'data/generations/{generation}/{published_name}',sha256=digest)
            if world:entry['global_tiles']={key:value for key,value in world[frame['time']].items()if key!='time'}
            public.append(entry)
        manifest=dict(report,frames=public,static_manifest_version=1,published_at=int(now),
                      rolling_horizon_hours=48,available_until=frames[-1]['time'],updating=False)
        if world:manifest['global_coverage']=True
        final.parent.mkdir(parents=True,exist_ok=True)
        if final.exists():
            raise ValueError('Generation already exists')
        stage.rename(final)
        path=output/'data/latest.json';temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(manifest,separators=(',',':')));temp.replace(path)
        health=dict(app='SeaPoint Radar',static_manifest_version=1,status='ready',
                    published_at=int(now),available_until=frames[-1]['time'],rolling_horizon_hours=48,
                    global_coverage=bool(world))
        (output/'health.json').write_text(json.dumps(health))
        # Old open pages keep their immutable URLs through source freshness expiry.
        for directory in final.parent.iterdir():
            if not directory.is_dir() or directory.name.startswith('.'):
                continue
            try:stamp=datetime.strptime(directory.name,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc).timestamp()
            except ValueError:continue
            if now-stamp>86400:shutil.rmtree(directory)
        return manifest
    finally:
        if stage.exists():shutil.rmtree(stage)


def build(output, cache, timeout=600):
    import os
    os.environ['SEAPOINT_FORECAST_CACHE']=str(cache/'gfs')
    os.environ['SEAPOINT_AROME_CACHE']=str(cache/'arome')
    write_shell(output)
    from forecast_service import RegionalForecastMaps
    from forecast_maps import ForecastMaps
    from global_forecast import CachedGFSReader, WorldTiles
    reader=CachedGFSReader(cache/'gfs-records')
    service=RegionalForecastMaps(gfs=ForecastMaps(reader=reader,horizon_hours=54),horizon_hours=54)
    world=WorldTiles(output/'data/world',reader=reader)
    deadline=time.monotonic()+timeout
    while True:
        report=service.snapshot()
        # Let each provider finish its current refresh. Publishing as soon as
        # cached GFS is complete would omit a regional update still decoding.
        if report.get('coverage_complete') and not report.get('updating'):
            gfs=service.gfs.snapshot()
            if gfs.get('status')=='ready'and gfs.get('coverage_complete')and not gfs.get('updating'):
                global_frames=world.prepare(gfs,time.time())
                # A build can cross an hourly/model boundary. Prepare its new
                # endpoint before publishing instead of shortening the buffer.
                report=service.snapshot()
                latest_gfs=service.gfs.snapshot()
                available={frame['time']for frame in global_frames}
                if (report.get('coverage_complete')and not report.get('updating')and
                    not latest_gfs.get('updating')and latest_gfs.get('model_run')==gfs.get('model_run')and
                    all(frame['time']in available for frame in report.get('frames',[]))):
                    manifest=publish_forecast(service,report,output,time.time(),global_frames)
                    world.prune(time.time());reader.prune(time.time())
                    return manifest
        if time.monotonic()>=deadline:
            # Fail the deployment; the last successful public site stays intact.
            raise TimeoutError('Buffered forecast could not be prepared; previous deployment retained')
        time.sleep(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--timeout',type=int,default=600)
    args=p.parse_args();manifest=build(args.output.resolve(),args.cache.resolve(),args.timeout)
    print(json.dumps({'frames':len(manifest['frames']),'published_at':manifest['published_at'],
                      'available_until':manifest['available_until'],'sources':manifest['source']}))
