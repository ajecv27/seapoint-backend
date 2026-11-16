import io
import json
import time
import unittest
from unittest.mock import patch
from http.client import HTTPConnection
from shapely.geometry import box, LineString
from shapely.strtree import STRtree
from marine_routing import engine
from marine_routing.guidance import guidance, match_leg, checked_path
from marine_routing.runtime import RoutingRuntime, DATASET
from tests.test_routing_http import server, StubRouting


class GuidanceTests(unittest.TestCase):
    def setUp(self):
        self.old = engine.LAND, engine.OSM_LAND, engine.DATASET
        self.land = box(-61.90, 17.08, -61.82, 17.15)
        engine.LAND = STRtree([self.land])
        engine.OSM_LAND = STRtree([self.land])
        engine.DATASET = {'id': DATASET}
        engine._prepared_coastline.cache_clear()
        checked_path.cache_clear()
        self.plan = ((-61.93,17.18),(-61.94,17.10),(-61.94,17.05),(-61.80,17.05),(-61.75,17.05))

    def tearDown(self):
        engine.LAND, engine.OSM_LAND, engine.DATASET = self.old
        engine._prepared_coastline.cache_clear()
        checked_path.cache_clear()

    def test_skipped_waypoints_rejoin_final_eastbound_leg(self):
        result = guidance((-61.78,17.0501), self.plan, 0, 4)
        self.assertEqual(result['active_leg'],3)
        self.assertEqual(result['points'][1],list(self.plan[-1]))
        self.assertFalse(result['depth_checked'])
        self.assertGreater(result['origin_radius_m'],0)

    def test_early_trip_keeps_first_leg_and_progress_never_rewinds(self):
        self.assertEqual(match_leg((-61.935,17.15),self.plan,0,4),0)
        self.assertEqual(match_leg(self.plan[0],self.plan,3,4),3)

    def test_far_off_plan_can_still_skip_obsolete_legs(self):
        self.assertEqual(match_leg((-61.78,17.045),self.plan,0,4),3)

    def test_near_parallel_legs_do_not_jump_ahead_due_to_gps_noise(self):
        points=((-62,17),(-61.99,17),(-61.99,17.00008),(-62,17.00008))
        self.assertEqual(match_leg((-61.995,17.00006),points,0,5),0)

    def test_course_connector_that_would_cross_land_is_rerouted(self):
        start=(-61.76,17.13)
        self.assertFalse(guidance_clear(start,self.plan[1]))
        with patch('marine_routing.guidance.match_leg',return_value=0):
            result=guidance(start,self.plan,0,4)
        points=result['points']
        self.assertEqual(result['mode'],'rerouted')
        self.assertTrue(all(not self.land.intersects(LineString((a,b))) for a,b in zip(points,points[1:])))
        self.assertEqual(points[0],list(start))
        self.assertEqual(points[-1],list(self.plan[-1]))

    def test_blocked_connector_can_continue_previously_checked_detour(self):
        # Force the original target to be on the other side of the island.
        planned=((-61.94,17.13),(-61.94,17.05),(-61.75,17.05))
        previous=((-61.76,17.13),(-61.76,17.07),(-61.75,17.05))
        with patch('marine_routing.guidance.match_leg',return_value=0), patch.object(engine,'route',side_effect=AssertionError('unnecessary A*')):
            result=guidance((-61.761,17.12),planned,0,4,previous)
        self.assertEqual(result['mode'],'continuing')

    def test_invalid_incoming_path_is_not_trusted(self):
        with self.assertRaisesRegex(ValueError,'crosses mapped land'):
            guidance((-61.95,17.12),((-61.95,17.12),(-61.76,17.12)),0,4)

    def test_osm_only_land_is_also_checked(self):
        engine.LAND=STRtree([])
        with self.assertRaises(ValueError):
            guidance((-61.95,17.12),((-61.95,17.12),(-61.76,17.12)),0,4)

    def test_arrival_needs_current_clear_final_connection(self):
        result=guidance((-61.75001,17.05001),self.plan,0,4)
        self.assertTrue(result['arrived'])
        self.assertEqual(result['active_leg'],3)

    def test_certified_origin_disk_keeps_updated_connectors_in_water(self):
        result=guidance((-61.78,17.0501),self.plan,0,4)
        origin,target=result['points'][:2]
        r=result['origin_radius_m']
        for dx,dy in ((r,0),(-r,0),(0,r),(0,-r)):
            moved=(origin[0]+dx/106400,origin[1]+dy/111132)
            self.assertTrue(guidance_clear(moved,target))
        self.assertIsNone(engine._DEADLINE)


def guidance_clear(a,b):
    from marine_routing.guidance import clear
    return clear(a,b)


class GuidanceProtocolTests(unittest.TestCase):
    def test_invalid_payload_never_starts_worker(self):
        runtime=RoutingRuntime()
        self.addCleanup(runtime.close)
        valid={'position':[-62,17],'planned':[[-62,17],[-61.9,17]],'active_leg':0,'accuracy_m':4}
        for change in ({'active_leg':True},{'active_leg':1},{'accuracy_m':float('nan')},
                       {'planned':[[-62,17]]},{'position':[0,90]},{'extra':1},
                       {'previous':[[-62,17],[-61.8,17]]}):
            with patch.object(runtime,'start',side_effect=AssertionError('started')):
                self.assertEqual(runtime.guidance(dict(valid,**change))[0],400)

    def test_worker_message_is_uncached_and_contains_no_recorded_track(self):
        runtime=RoutingRuntime();self.addCleanup(runtime.close)
        request={'position':[-62,17],'planned':[[-62,17],[-61.9,17]],'active_leg':0,'accuracy_m':4}
        with patch.object(runtime,'_execute',return_value=(200,{})) as execute:
            runtime.guidance(request)
        payload,key=execute.call_args.args
        self.assertIsNone(key)
        self.assertEqual(payload['op'],'guidance')
        self.assertNotIn('track',payload)

    def test_post_bounded_json_cors_and_no_private_logs(self):
        class Stub(StubRouting):
            def guidance(self,body): self.calls.append(body);return 200,{'status':'ok'}
        stub=Stub();logs=io.StringIO()
        with patch('sys.stderr',logs), server(stub) as port:
            connection=HTTPConnection('127.0.0.1',port,timeout=3)
            connection.request('POST','/routing/guidance',json.dumps({'position':[-61.987654,17.123456]}),{'Content-Type':'application/json'})
            response=connection.getresponse();response.read()
            self.assertEqual(response.status,200)
            self.assertIn('POST',response.getheader('Access-Control-Allow-Methods'))
            self.assertEqual(response.getheader('Cache-Control'),'no-store')
            connection.close()
            for body,content_type in (('broken','application/json'),('{}','text/plain')):
                connection=HTTPConnection('127.0.0.1',port,timeout=3)
                connection.request('POST','/routing/guidance',body,{'Content-Type':content_type})
                response=connection.getresponse();response.read()
                self.assertEqual(response.status,400);connection.close()
        self.assertEqual(len(stub.calls),1)
        self.assertNotIn('17.123456',logs.getvalue())
        self.assertNotIn('61.987654',logs.getvalue())


class ReleasedGuidanceWorkerTests(unittest.TestCase):
    def test_real_worker_guidance_protocol_and_coast_checks(self):
        import importlib.util
        if importlib.util.find_spec('seapoint_coast_data') is None:
            self.skipTest('released coast package not installed')
        runtime=RoutingRuntime(startup_timeout=30)
        self.addCleanup(runtime.close)
        runtime.start()
        deadline=time.monotonic()+30
        while time.monotonic()<deadline and runtime.health()['status']!='ready':
            time.sleep(.05)
        self.assertEqual(runtime.health()['status'],'ready')
        self.assertEqual(runtime.health()['guidance_version'],'live-coast-guidance-v1')
        # Generic public open-water waypoints, not a recorded trip or live fix.
        planned=[[-62.0,17.3],[-62.0,17.32],[-61.98,17.32],[-61.96,17.32]]
        status,result=runtime.guidance({'position':[-61.969,17.32005],
            'planned':planned,'active_leg':0,'accuracy_m':4})
        self.assertEqual(status,200,result)
        self.assertEqual(result['active_leg'],2)
        self.assertEqual(result['points'][-1],planned[-1])
        self.assertGreater(result['origin_radius_m'],0)
        self.assertFalse(result['depth_checked'])
        self.assertEqual(runtime.health()['status'],'ready')
