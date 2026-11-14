import importlib.util
import unittest
from unittest.mock import patch
from shapely.geometry import box
from marine_routing.coast_data import load_coast, select_routing_coast


class PolicyIndexValidationTests(unittest.TestCase):
    def test_corrupt_index_is_rejected_before_selection(self):
        with patch('marine_routing.coast_data.Path.read_bytes', return_value=b'corrupt'):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                select_routing_coast([box(-62,17,-61.9,17.1)], [box(-62,17,-61.9,17.1)], {})

    def test_stale_dataset_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'does not match'):
            select_routing_coast([box(-62,17,-61.9,17.1)], [box(-62,17,-61.9,17.1)],
                                {'id':'old-release', 'sha256':'0'*64})

    @unittest.skipUnless(importlib.util.find_spec('seapoint_coast_data'), 'released coast package not installed')
    def test_index_selects_exactly_the_same_features_as_the_geometry_predicates(self):
        land, osm, manifest = load_coast()
        gshhg = land[:manifest['sources'][0]['features']]
        expected = select_routing_coast(gshhg, osm)
        actual = select_routing_coast(gshhg, osm, manifest)
        self.assertEqual(len(actual), len(expected))
        self.assertTrue(all(a is b for a, b in zip(actual, expected)))
