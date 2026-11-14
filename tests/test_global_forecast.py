"""World coverage, projection, immutable tile reuse and source validation."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,math,types
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
from global_forecast import BOUNDS,CachedGFSReader,WorldTiles,world_image
from forecast_service import RegionalForecastMaps
from static_site.export import publish_forecast
from test_forecast_service import Provider,report,RUN,NOW
from test_static_site import png


class GlobalForecastTests(unittest.TestCase):
    def test_source_decoder_rejects_wrong_time_units_coverage_and_missing_values(self):
        from forecast_maps import decode_gfs
        stamp=RUN+3600;date=datetime.fromtimestamp(stamp,timezone.utc)
        good={'validityDate':int(date.strftime('%Y%m%d')),'validityTime':int(date.strftime('%H%M')),
              'shortName':'prate','stepType':'instant','units':'kg m**-2 s**-1',
              'Ni':1440,'Nj':721,'jScansPositively':0,'iScansNegatively':0,
              'gridType':'regular_ll','numberOfMissing':0,
              'latitudeOfFirstGridPointInDegrees':90,'longitudeOfFirstGridPointInDegrees':0,
              'latitudeOfLastGridPointInDegrees':-90,'longitudeOfLastGridPointInDegrees':359.75,
              'iDirectionIncrementInDegrees':.25,'jDirectionIncrementInDegrees':.25}
        current=dict(good);values=np.zeros(721*1440);released=[]
        ec=types.SimpleNamespace(codes_new_from_message=lambda data:1,codes_get=lambda handle,key:current[key],codes_get_values=lambda handle:values,codes_release=lambda handle:released.append(handle))
        with patch.dict('sys.modules',{'eccodes':ec}):
            self.assertEqual(decode_gfs(b'GRIB',stamp).shape,(721,1440))
            for key,value in [('validityTime',good['validityTime']+100),('units','mm'),('stepType','accum'),('longitudeOfFirstGridPointInDegrees',180),('numberOfMissing',1),('jScansPositively',1)]:
                current=dict(good);current[key]=value
                with self.assertRaises(ValueError):decode_gfs(b'GRIB',stamp)
            current=dict(good);values[0]=np.nan
            with self.assertRaises(ValueError):decode_gfs(b'GRIB',stamp)
        self.assertEqual(len(released),8)

    def test_record_cache_shares_exact_range_and_rejects_corruption(self):
        calls=[]
        def reader(url,span=None):calls.append((url,span));return b'public source '+repr(span).encode()
        with tempfile.TemporaryDirectory()as directory:
            cache=CachedGFSReader(directory,reader)
            self.assertEqual(cache('https://example.test/a',(0,20)),cache('https://example.test/a',(0,20)))
            self.assertEqual(len(calls),1)
            next(Path(directory).glob('*.record')).write_bytes(b'corrupt')
            self.assertEqual(cache('https://example.test/a',(0,20)),b'public source (0, 20)')
            self.assertEqual(len(calls),2)
            cache('https://example.test/a',(21,40));self.assertEqual(len(calls),3)

    def test_projection_covers_four_continents_and_wraps_the_date_line(self):
        lat=90-np.arange(721)*.25;lon=np.arange(1440)*.25
        values=np.zeros((721,1440))
        points=[(40.7,-74),(51.5,-.12),(-33.9,151.2),(-33.9,18.4),(20,179.8)]
        for north,east in points:
            delta=(lon-east+180)%360-180
            values[np.ix_(abs(lat-north)<2,abs(delta)<2)]=5/3600
        image=world_image(values,max_zoom=1).convert('RGBA');side=image.width
        for north,east in points:
            x=int((east+180)/360*side)%side
            y=int((1-math.asinh(math.tan(math.radians(north)))/math.pi)/2*side)
            self.assertGreater(image.getpixel((x,y))[3],150,(north,east))
        y=int((1-math.asinh(math.tan(math.radians(20)))/math.pi)/2*side)
        self.assertGreater(image.getpixel((0,y))[3],150)
        self.assertGreater(image.getpixel((side-1,y))[3],150)
        self.assertEqual(image.getpixel((side//2,side//2))[3],0)

    def test_tiles_reuse_verified_assets_and_rebuild_corrupt_data(self):
        calls=[]
        def reader(url,span=None):
            calls.append((url,span))
            return b'1:0:x:PRATE:surface:1 hour fcst:\n2:30:x:APCP:surface:acc fcst:\n'if url.endswith('.idx')else b'GRIB'
        with tempfile.TemporaryDirectory()as directory,patch('global_forecast.decode_gfs',return_value=np.full((721,1440),5/3600)):
            world=WorldTiles(directory,reader,max_zoom=1)
            descriptor=world.frame(RUN,RUN+3600)
            files=list(Path(directory).rglob('*.png'))
            self.assertEqual(len(files),5)
            for file in files:
                with Image.open(file)as image:self.assertEqual(image.size,(256,256));self.assertGreater(image.convert('RGBA').getpixel((128,128))[3],150)
            world.frame(RUN,RUN+3600);self.assertEqual(len(calls),2)
            files[0].write_bytes(b'broken')
            self.assertEqual(world.frame(RUN,RUN+3600),descriptor);self.assertEqual(len(calls),4)
            next(Path(directory).rglob('ready.json')).write_text('[]')
            world.frame(RUN,RUN+3600);self.assertEqual(len(calls),6)
            self.assertFalse(list(Path(directory).glob('.building-*')))
            before={str(p.relative_to(directory)):p.read_bytes()for p in Path(directory).rglob('*')if p.is_file()}
            with patch.object(world,'_reuse',return_value=False),patch('global_forecast.decode_gfs',side_effect=ValueError('bad source')):
                with self.assertRaises(ValueError):world.frame(RUN,RUN+3600)
            after={str(p.relative_to(directory)):p.read_bytes()for p in Path(directory).rglob('*')if p.is_file()}
            self.assertEqual(before,after)

    def descriptor(self,run,stamp):
        cycle=datetime.fromtimestamp(run,timezone.utc).strftime('%Y%m%d%H');hour=(stamp-run)//3600
        return dict(time=stamp,model_run=run,fetched_at=NOW,source='NOAA GFS',units='mm/h',resolution_km=28,bounds=BOUNDS,max_zoom=4,tile_size=256,url_template=f'data/world/{cycle}-{hour:03d}-g1/{{z}}/{{x}}/{{y}}.png')

    def test_prepare_validates_complete_real_source_times_before_any_tile_build(self):
        with tempfile.TemporaryDirectory()as directory:
            world=WorldTiles(directory)
            data=report(last=61)
            with patch.object(world,'frame',side_effect=self.descriptor)as make:
                result=world.prepare(data,NOW)
                self.assertGreaterEqual(result[-1]['time'],NOW+54*3600)
                self.assertEqual(len(result),56)
                self.assertEqual(make.call_count,56)
            for change in ('gap','old','units'):
                bad=deepcopy(data)
                if change=='gap':bad['frames'].pop(10)
                elif change=='old':bad['model_run']-=86400
                else:bad['units']='in/h'
                with patch.object(world,'frame')as make:
                    with self.assertRaises(ValueError):world.prepare(bad,NOW)
                    make.assert_not_called()

    def test_publication_combines_global_coverage_with_fine_regional_source(self):
        service=RegionalForecastMaps(gfs=Provider(report(last=61)),arome=Provider(report('arome')),clock=lambda:NOW,horizon_hours=54)
        service.image=lambda name:png();data=service.snapshot()
        descriptors=[self.descriptor(RUN,frame['time'])for frame in data['frames']]
        with tempfile.TemporaryDirectory()as directory:
            output=Path(directory)
            manifest=publish_forecast(service,data,output,NOW,descriptors)
            self.assertTrue(manifest['global_coverage'])
            self.assertTrue(json.loads((output/'health.json').read_text())['global_coverage'])
            self.assertEqual(manifest['frames'][0]['provider'],'arome-antilles')
            self.assertEqual(manifest['frames'][0]['resolution_km'],2.5)
            self.assertEqual(manifest['frames'][0]['global_tiles']['resolution_km'],28)
            self.assertEqual(manifest['frames'][0]['global_tiles']['bounds'],BOUNDS)
            saved=(output/'data/latest.json').read_bytes()
            for change in ('missing','wrong URL','expired'):
                bad=deepcopy(descriptors)
                if change=='missing':bad.pop(7)
                elif change=='wrong URL':bad[0]['url_template']=bad[1]['url_template']
                else:bad[0]['model_run']-=86400
                with self.assertRaises(ValueError):publish_forecast(service,data,output,NOW+1,bad)
                self.assertEqual((output/'data/latest.json').read_bytes(),saved)

    def test_pruning_keeps_assets_through_model_freshness_expiry(self):
        with tempfile.TemporaryDirectory()as directory:
            world=WorldTiles(directory)
            for name,age in [('valid',24*3600),('expired',26*3600)]:
                p=Path(directory)/name;p.mkdir();(p/'ready.json').write_text(json.dumps({'model_run':NOW-age}))
            world.prune(NOW)
            self.assertTrue((Path(directory)/'valid').exists());self.assertFalse((Path(directory)/'expired').exists())

if __name__=='__main__':unittest.main()
