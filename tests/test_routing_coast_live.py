"""Integration checks against the exact released coastline package, when installed."""
import importlib.util
import unittest
from shapely.geometry import LineString
from marine_routing import engine


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


if __name__ == '__main__':
    unittest.main()
