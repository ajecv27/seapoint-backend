"""Static publication must preserve forecast identity and survive failed builds."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from forecast_maps import ForecastMaps
from forecast_service import RegionalForecastMaps, HOUR
from static_site.export import build, publish_forecast, static_html
from test_forecast_service import Provider, report, RUN, NOW


def png():
    output = BytesIO()
    Image.new('RGBA', (640, 640), (12, 90, 150, 180)).save(output, format='PNG')
    return output.getvalue()


class StaticPublicationTests(unittest.TestCase):
    def service(self, **kwargs):
        service = RegionalForecastMaps(
            gfs=Provider(report(last=61)), arome=Provider(report('arome')),
            clock=lambda: NOW, horizon_hours=54, **kwargs)
        service.image = lambda name: png()
        return service

    def test_buffer_keeps_a_complete_48_hours_between_hourly_publications(self):
        service = self.service()
        buffered = service.snapshot()
        self.assertTrue(buffered['coverage_complete'])
        self.assertGreaterEqual(buffered['frames'][-1]['time'], NOW + 54*HOUR)
        for later in (NOW, NOW+HOUR, NOW+5*HOUR):
            self.assertGreaterEqual(buffered['frames'][-1]['time'], later+48*HOUR)
        default = RegionalForecastMaps(gfs=service.gfs, arome=service.arome,
                                      clock=lambda: NOW).snapshot()
        self.assertEqual(default['horizon_hours'], 48)
        self.assertEqual(default['forecast_until'], int(NOW+48*HOUR))
        self.assertEqual(len(buffered['frames'])-len(default['frames']), 6)

    def test_bounded_horizon_rejects_invalid_values(self):
        for value in (True, 47, 73, 54.0, '54'):
            with self.assertRaises(ValueError):
                RegionalForecastMaps(horizon_hours=value)
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    ForecastMaps(directory=directory, horizon_hours=value)

    def test_images_are_immutable_relative_urls_and_keep_source_times(self):
        service = self.service()
        # The sources can have different fetch and model issue times.
        service.arome.value = report('arome', run=RUN+6*HOUR, first=1)
        service.arome.value['fetched_at'] = int(NOW)
        service.gfs.value['fetched_at'] = RUN+5*HOUR
        data = service.snapshot()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            manifest=publish_forecast(service, data, output, NOW)
            self.assertEqual(json.loads((output/'data/latest.json').read_text()),manifest)
            self.assertEqual(manifest['fetched_at'], RUN+5*HOUR)
            self.assertEqual(manifest['model_run'], data['model_run'])
            self.assertEqual(manifest['published_at'], NOW)
            self.assertEqual({f['provider'] for f in manifest['frames']}, {'arome-antilles','noaa-gfs'})
            for frame in manifest['frames']:
                self.assertFalse(frame['url'].startswith('/'))
                contents=(output/frame['url']).read_bytes()
                self.assertEqual(frame['sha256'], hashlib.sha256(contents).hexdigest())
                original=next(f for f in data['frames'] if f['time']==frame['time'])
                for key in ('provider','model_run','bounds','value_semantics','period_seconds'):
                    self.assertEqual(frame[key], original[key])
            health=json.loads((output/'health.json').read_text())
            self.assertEqual(health['available_until'],manifest['frames'][-1]['time'])

    def test_incomplete_or_corrupt_build_preserves_last_success(self):
        service=self.service()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            publish_forecast(service, service.snapshot(), output, NOW)
            saved=(output/'data/latest.json').read_bytes()
            health=(output/'health.json').read_bytes()
            broken=service.snapshot();broken['frames'].pop(8)
            with self.assertRaises(ValueError):
                publish_forecast(service, broken, output, NOW+1)
            count=0
            def corrupt(name):
                nonlocal count
                count+=1
                return png() if count<8 else b'broken PNG'
            service.image=corrupt
            with self.assertRaises(ValueError):
                publish_forecast(service, service.snapshot(), output, NOW+1)
            self.assertEqual((output/'data/latest.json').read_bytes(), saved)
            self.assertEqual((output/'health.json').read_bytes(), health)
            self.assertFalse(list((output/'data/generations').glob('.building-*')))

    def test_old_generation_retained_for_open_pages_then_expires(self):
        service=self.service()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            first=publish_forecast(service, service.snapshot(), output, NOW)
            old_file=output/first['frames'][0]['url']
            publish_forecast(service, service.snapshot(), output, NOW+1)
            self.assertTrue(old_file.exists())
            stale=output/'data/generations/20260101T000000Z'
            stale.mkdir();(stale/'obsolete.png').write_bytes(png())
            publish_forecast(service, service.snapshot(), output, NOW+2)
            self.assertFalse(stale.exists())

    def test_stale_source_is_not_republished_as_new_weather(self):
        service=self.service()
        data=service.snapshot()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                publish_forecast(service,data,Path(directory),RUN+24*HOUR)

    def test_static_page_removes_render_and_cdn_script_dependencies(self):
        html=static_html()
        for path in ("'/radar-frames'","'/forecast-frames'","'/basemap-style'",'onrender.com','https://unpkg.com/'):
            self.assertNotIn(path,html)
        self.assertIn('https://api.rainviewer.com/public/weather-maps.json',html)
        self.assertIn("'data/latest.json?v='",html)
        self.assertIn('vendor/NOTICE.txt',html)
        self.assertIn('vendor/leaflet.js',html)
        self.assertIn('available_until>=now+48*3600',html)

    def test_scheduled_build_waits_for_regional_refresh_before_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)
            with patch('static_site.export.write_shell'), patch('forecast_service.RegionalForecastMaps') as factory, patch('static_site.export.time.sleep'), patch('static_site.export.publish_forecast') as publish:
                factory.return_value.snapshot.side_effect=[
                    {'coverage_complete':True,'updating':True},
                    {'coverage_complete':True,'updating':False,'source':'regional update'}]
                build(output,output/'cache')
                self.assertEqual(factory.return_value.snapshot.call_count,2)
                self.assertEqual(publish.call_args.args[1]['source'],'regional update')


if __name__=='__main__':unittest.main()
