"""A simple land/water style derived from OpenFreeMap's actual Liberty style."""
from copy import deepcopy


LAND_COLOR = '#4d8958'
WATER_COLOR = '#183d63'
COAST_COLOR = '#142e28'


def style_document(document):
    """Return a copy with flat colours and place labels, without aerial imagery.

    Keep the provider's source URLs, glyphs, sprite and attribution intact. The
    caller can add a separate subtle terrain overlay; this vector style itself
    contains no shaded imagery, relief, roads, buildings or 3D geometry.
    """
    result = deepcopy(document)
    layers = []
    for layer in result.get('layers', []):
        layer_id = layer.get('id', '')
        layer_type = layer.get('type')
        if layer_id == 'background' and layer_type == 'background':
            layer['paint'] = {'background-color': LAND_COLOR}
            layers.append(layer)
        elif layer_id == 'water' and layer_type == 'fill':
            layer['paint'] = {
                'fill-color': WATER_COLOR,
                'fill-antialias': True,
                'fill-outline-color': COAST_COLOR,
            }
            layers.append(layer)
        elif layer_type == 'symbol' and layer_id in {
            'label_village', 'label_town', 'label_city', 'label_city_capital',
            'label_country_1', 'label_country_2', 'label_country_3',
        }:
            country = layer_id.startswith('label_country_')
            if country:
                layer['maxzoom'] = 9
            else:
                layer['minzoom'] = 9 if layer_id == 'label_village' else 8
                layer.pop('maxzoom', None)
            layer['paint'] = {
                'text-color': '#ffffff',
                'text-halo-color': '#102b38',
                'text-halo-width': 1.5,
                'text-halo-blur': 0.5,
            }
            layout = layer.setdefault('layout', {})
            # Retain actual multilingual name fields and available provider
            # fonts, while removing optional icons or icon-derived offsets.
            for key in list(layout):
                if key.startswith('icon-'):
                    del layout[key]
            layout['text-anchor'] = 'center'
            layout['text-offset'] = [0, 0]
            layout['text-allow-overlap'] = False
            layout['text-ignore-placement'] = False
            layers.append(layer)
    result['layers'] = layers
    # This removed raster source is not needed by any retained layer. Keeping
    # it would leave an unnecessary terrain TileJSON/provider dependency.
    result.get('sources', {}).pop('ne2_shaded', None)
    return result
