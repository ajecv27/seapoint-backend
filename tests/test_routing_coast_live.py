"""Integration checks against the exact released coastline package, when installed."""
import importlib.util
import unittest
from shapely.geometry import LineString
from marine_routing import engine
from marine_routing import COASTLINE_POLICY


@unittest.skipUnless(importlib.util.find_spec('seapoint_coast_data'), 'released coast package not installed')
class ReleasedCoastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = engine.initialize()
        engine._prepared_coastline.cache_clear()

    def test_real_island_routes_avoid_the_released_coast(self):
        self.assertEqual(self.manifest['id'], 'caribbean-osm-gshhg-20261114-v1')
        examples = [
            ((-61.9, 17.08), (-61.65, 17.08)),  # Around Antigua.
            ((-61.89, 17.07), (-61.803, 16.304)),  # Guadeloupe.
            ((-61.894, 17.066), (-62.66, 17.14)),  # Nevis.
            ((-82.5, 21.5), (-81, 21)),  # Cuba.
            ((-64.9, 32.25), (-64.6, 32.4)),  # Bermuda.
        ]
        for start, finish in examples:
            with self.subTest(start=start, finish=finish):
                result = engine.route(start, finish)
                self.assertFalse(result['depth_checked'])
                points = [(p['lon'], p['lat']) for p in result['points']]
                self.assertGreaterEqual(len(points), 2)
                for a, b in zip(points, points[1:]):
                    segment = LineString((a, b))
                    self.assertFalse(any(engine.LAND.geometries[int(i)].intersects(segment)
                                         for i in engine.LAND.query(segment)))

    def test_land_and_outside_coverage_do_not_become_direct_routes(self):
        for start in [(-61.8, 17.1), (0, 0)]:
            with self.assertRaises(ValueError):
                engine.route(start, (-61.9, 17.08))

    def test_st_johns_to_jolly_fuel_dock_and_back_use_the_marina_entrance(self):
        # Public harbour/fuel-building coordinates; these are not recorded GPS.
        st_johns = (-61.859, 17.122)
        fuel_building = (-61.88385, 17.06684)
        for start, finish in [(st_johns, fuel_building), (fuel_building, st_johns)]:
            with self.subTest(start=start):
                route = engine.route(start, finish, seconds=8)
                self.assertEqual(route['coastline_policy'], COASTLINE_POLICY)
                self.assertFalse(route['depth_checked'])
                points = [(p['lon'], p['lat']) for p in route['points']]
                self.assertGreater(len(points), 2)
                self.assertLessEqual(route['adjusted_start_m'], 75)
                self.assertLessEqual(route['adjusted_destination_m'], 75)
                for a, b in zip(points, points[1:]):
                    self.assertTrue(engine.clear_segment(a, b))
                    segment = LineString((a, b))
                    self.assertFalse(any(engine.OSM_LAND.geometries[int(i)].intersects(segment)
                                         for i in engine.OSM_LAND.query(segment)))
                # The fuel building is inside the basin. Its near-shore
                # adjustment must be small and the route must go via the inlet.
                self.assertTrue(any(-61.891 < x < -61.888 and 17.072 < y < 17.074
                                    for x, y in points))
                self.assertGreater(route['distance_nm'], 6)
                self.assertLess(route['distance_nm'], 11)

    def test_nearby_jolly_harbour_arm_also_connects_to_open_water(self):
        route = engine.route((-61.859, 17.122), (-61.8893, 17.075), seconds=6)
        self.assertEqual(route['status'], 'ok')
        self.assertLessEqual(route['adjusted_destination_m'], 75)


if __name__ == '__main__':
    unittest.main()
