import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import shapely
from shapely.geometry import box, LineString, Point
from shapely.strtree import STRtree

from marine_routing import engine
from marine_routing.coast_data import load_coast
from marine_routing.runtime import RoutingRuntime, DATASET


class CoastDataTests(unittest.TestCase):
    def make(self, folder):
        geometry = shapely.to_wkb(box(-62, 17, -61.9, 17.1), byte_order=1)
        raw = b'SPCOAST1\n' + struct.pack('<I', 200)
        for group in (0, 1):
            raw += (struct.pack('<BI', group, len(geometry)) + geometry) * 100
        compressed = gzip.compress(raw, mtime=0)
        manifest = {'format':'SPCOAST1', 'crs':'EPSG:4326', 'bounds':[-94.0,5.0,-55.0,34.0],
            'uncompressed_bytes':len(raw), 'compressed_bytes':len(compressed),
            'sha256':hashlib.sha256(compressed).hexdigest(),
            'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),
            'sources':[{'features':100},{'features':100}]}
        (folder/'manifest.json').write_text(json.dumps(manifest))
        (folder/'caribbean-v1.bin.gz').write_bytes(compressed)
        return manifest

    def test_verified_geometry_loads_and_keeps_osm_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); self.make(folder)
            all_land, osm, _ = load_coast(folder)
            self.assertEqual((len(all_land),len(osm)), (200,100))

    def test_missing_corrupt_wrong_crs_and_truncated_packages_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); manifest=self.make(folder)
            data=folder/'caribbean-v1.bin.gz'
            data.write_bytes(data.read_bytes()[:-1])
            with self.assertRaises(ValueError): load_coast(folder)
            self.make(folder)
            manifest['crs']='EPSG:3857';(folder/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError): load_coast(folder)
            self.make(folder);data.unlink()
            with self.assertRaises(OSError):load_coast(folder)

    def test_decompression_size_limit_fails_before_accepting_bomb(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);manifest=self.make(folder)
            raw=b'x'*2048;compressed=gzip.compress(raw)
            manifest.update(uncompressed_bytes=1000,compressed_bytes=len(compressed),sha256=hashlib.sha256(compressed).hexdigest())
            (folder/'manifest.json').write_text(json.dumps(manifest));(folder/'caribbean-v1.bin.gz').write_bytes(compressed)
            with patch('marine_routing.coast_data.MAX_EXPANDED_BYTES',1024):
                with self.assertRaises(ValueError):load_coast(folder)


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.old=(engine.LAND,engine.OSM_LAND,engine.DATASET)
        self.land=box(-61.90,17.08,-61.82,17.15)
        engine.LAND=STRtree([self.land]);engine.OSM_LAND=STRtree([self.land]);engine.DATASET={'id':DATASET}
        engine._prepared_coastline.cache_clear()

    def tearDown(self):
        engine.LAND,engine.OSM_LAND,engine.DATASET=self.old
        engine._prepared_coastline.cache_clear()

    def test_route_detours_around_land_and_exact_response_segments_are_clear(self):
        start=(-61.95,17.12);finish=(-61.76,17.12)
        self.assertTrue(self.land.intersects(LineString((start,finish))))
        result=engine.route(start,finish,seconds=3)
        points=[(p['lon'],p['lat'])for p in result['points']]
        self.assertGreater(len(points),2)
        self.assertTrue(all(not self.land.intersects(LineString((a,b)))for a,b in zip(points,points[1:])))
        self.assertFalse(result['depth_checked'])

    def test_clear_open_water_may_use_a_direct_leg(self):
        result=engine.route((-62,17.3),(-61.6,17.3),seconds=1)
        self.assertEqual(len(result['points']),2)

    def test_no_route_is_an_error_not_a_straight_line_fallback(self):
        with patch.object(engine,'astar_route',return_value=None):
            with self.assertRaisesRegex(ValueError,'No water-only route'):
                engine.route((-61.95,17.12),(-61.76,17.12),seconds=1)

    def test_inland_endpoints_nonfinite_outside_coverage_and_deadline_fail(self):
        with self.assertRaisesRegex(ValueError,'mapped land'):
            engine.route((-61.86,17.12),(-61.76,17.12),seconds=1)
        for point in [(float('nan'),17),(-20,17),(-62,50)]:
            with self.assertRaises(ValueError):engine.route(point,(-61.6,17.3))
        with self.assertRaises(engine.RouteTimeout):engine.route((-62,17.3),(-61.6,17.3),seconds=0)

    def test_endpoint_adjustment_is_small_and_result_stays_on_water(self):
        result=engine.route((-61.8999,17.11),(-61.95,17.3),seconds=2)
        self.assertLessEqual(result['adjusted_start_m'],75.1)
        first=result['points'][0]
        self.assertFalse(self.land.covers(Point(first['lon'],first['lat'])))


class RuntimeTests(unittest.TestCase):
    def make(self,mode='normal',**kwargs):
        runtime=RoutingRuntime(command=[sys.executable,str(Path(__file__).with_name('routing_fixture_worker.py')),mode],**kwargs)
        self.addCleanup(runtime.close)
        runtime.start()
        return runtime

    def ready(self,runtime):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            if runtime.health()['status']=='ready':return
            time.sleep(.01)
        self.fail('Worker did not become ready')

    def test_success_cache_survives_worker_death_and_never_restarts_for_cache(self):
        runtime=self.make();self.ready(runtime)
        status,body=runtime.route((-62,17),(-61.7,17))
        self.assertEqual(status,200)
        runtime._process.kill();runtime._process.wait()
        self.assertEqual(runtime.route((-62,17),(-61.7,17)),(status,body))

    def test_busy_route_keeps_health_fast_and_rejects_parallel_work(self):
        runtime=self.make('slow');self.ready(runtime)
        result=[];thread=threading.Thread(target=lambda:result.append(runtime.route((-62,17),(-61.7,17))))
        thread.start();time.sleep(.05)
        started=time.monotonic();self.assertEqual(runtime.health()['status'],'ready')
        self.assertLess(time.monotonic()-started,.1)
        status,body=runtime.route((-62.1,17),(-61.8,17))
        self.assertEqual(status,429);self.assertTrue(body['retryable'])
        thread.join(3);self.assertEqual(result[0][0],200)

    def test_hung_worker_is_retired_and_new_requests_can_recover(self):
        runtime=self.make('hung',route_timeout=.15);self.ready(runtime)
        started=time.monotonic();status,_=runtime.route((-62,17),(-61.7,17))
        self.assertEqual(status,504);self.assertLess(time.monotonic()-started,2)
        runtime.command=[sys.executable,str(Path(__file__).with_name('routing_fixture_worker.py')),'normal']
        runtime.start();self.ready(runtime)
        self.assertEqual(runtime.route((-62,17),(-61.7,17))[0],200)

    def test_warmup_and_invalid_coordinates_do_not_return_invented_routes(self):
        runtime=self.make('slow-start',startup_timeout=.1)
        status,body=runtime.route((-62,17),(-61.7,17))
        self.assertEqual(status,503);self.assertTrue(body['retryable']);self.assertNotIn('points',body)
        self.assertEqual(runtime.route((float('inf'),17),(-61.7,17))[0],400)
        self.assertEqual(runtime.route((-62,17),(-62,17))[0],400)


if __name__=='__main__':unittest.main()
