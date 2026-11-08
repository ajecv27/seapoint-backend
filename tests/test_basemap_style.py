from copy import deepcopy
import unittest

from basemap_style import style_document


class BasemapStyleTests(unittest.TestCase):
    def setUp(self):
        self.document = {
            'version': 8,
            'name': 'OpenFreeMap Liberty',
            'glyphs': 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
            'sprite': 'https://tiles.openfreemap.org/sprites/ofm_f384/ofm',
            'sources': {
                'openmaptiles': {
                    'type': 'vector', 'url': 'https://tiles.openfreemap.org/planet',
                    'attribution': '© OpenFreeMap © OpenMapTiles © OpenStreetMap contributors',
                },
                'ne2_shaded': {'type': 'raster', 'tiles': ['https://example.test/terrain/{z}/{x}/{y}.png']},
            },
            'layers': [
                {'id': 'background', 'type': 'background', 'paint': {'background-color': '#fff'}},
                {'id': 'natural_earth', 'type': 'raster', 'source': 'ne2_shaded'},
                {'id': 'water', 'type': 'fill', 'source': 'openmaptiles', 'source-layer': 'water'},
                {'id': 'road', 'type': 'line', 'source': 'openmaptiles', 'source-layer': 'transportation'},
                {'id': 'building-3d', 'type': 'fill-extrusion', 'source': 'openmaptiles'},
                {'id': 'landcover_grass', 'type': 'fill', 'source': 'openmaptiles'},
                {'id': 'label_country_1', 'type': 'symbol', 'source': 'openmaptiles',
                 'source-layer': 'place', 'minzoom': 0, 'layout': {'text-field': ['get', 'name']}},
                {'id': 'label_town', 'type': 'symbol', 'source': 'openmaptiles',
                 'source-layer': 'place', 'minzoom': 6, 'layout': {
                     'text-field': ['get', 'name_en'], 'text-font': ['Noto Sans Regular'],
                     'icon-image': 'city-dot', 'text-offset': [0, 1]}},
                {'id': 'label_village', 'type': 'symbol', 'source': 'openmaptiles',
                 'source-layer': 'place', 'layout': {'text-field': ['get', 'name']}},
            ],
        }

    def test_preserves_real_vector_source_and_attribution_without_mutation(self):
        before = deepcopy(self.document)
        result = style_document(self.document)
        self.assertEqual(self.document, before)
        self.assertEqual(result['sources']['openmaptiles'], before['sources']['openmaptiles'])
        self.assertEqual(result['glyphs'], before['glyphs'])
        self.assertEqual(result['sprite'], before['sprite'])
        self.assertNotIn('ne2_shaded', result['sources'])

    def test_flat_land_water_and_coast_colours(self):
        layers = {layer['id']: layer for layer in style_document(self.document)['layers']}
        self.assertEqual(layers['background']['paint']['background-color'], '#4d8958')
        self.assertEqual(layers['water']['paint']['fill-color'], '#183d63')
        self.assertEqual(layers['water']['paint']['fill-outline-color'], '#142e28')

    def test_removes_imagery_relief_buildings_and_road_clutter(self):
        result = style_document(self.document)
        self.assertFalse(any(layer['type'] in ('raster', 'fill-extrusion') for layer in result['layers']))
        ids = {layer['id'] for layer in result['layers']}
        self.assertFalse(ids & {'natural_earth', 'road', 'building-3d', 'landcover_grass'})

    def test_preserves_place_names_and_sets_readable_label_visibility(self):
        layers = {layer['id']: layer for layer in style_document(self.document)['layers']}
        self.assertEqual(layers['label_country_1']['maxzoom'], 9)
        self.assertEqual(layers['label_town']['minzoom'], 8)
        self.assertEqual(layers['label_village']['minzoom'], 9)
        town = layers['label_town']
        self.assertEqual(town['layout']['text-field'], ['get', 'name_en'])
        self.assertEqual(town['layout']['text-font'], ['Noto Sans Regular'])
        self.assertNotIn('icon-image', town['layout'])
        self.assertEqual(town['paint']['text-color'], '#ffffff')
        self.assertGreater(town['paint']['text-halo-width'], 0)


if __name__ == '__main__':
    unittest.main()
