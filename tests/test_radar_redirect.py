"""Exercise the production HTTP handler without starting weather providers."""
import ast
from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import unittest
from urllib.parse import parse_qs, urlencode, urlparse


@contextmanager
def server():
    # cloud_server also starts the listener at module scope. Load its actual
    # handler alone so tests can check HTTP behavior with providers unavailable.
    tree = ast.parse(Path(__file__).resolve().parents[1].joinpath('cloud_server.py').read_text())
    handler = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Handler')
    namespace = dict(BaseHTTPRequestHandler=BaseHTTPRequestHandler, parse_qs=parse_qs,
                     urlencode=urlencode, urlparse=urlparse)
    exec(compile(ast.Module(body=[handler], type_ignores=[]), 'cloud_server.py', 'exec'), namespace)
    production_handler = namespace['Handler']
    production_handler.log_message = lambda *_: None
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), production_handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_port
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


class RadarRedirectTests(unittest.TestCase):
    def request(self, port, method, path):
        connection = HTTPConnection('127.0.0.1', port, timeout=5)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_old_radar_link_preserves_location_and_does_not_need_providers(self):
        with server() as port:
            query = urlencode({'lat': '17.16', 'lon': '-61.835',
                               'name': 'North & Northwest Coast – Overview', 'ui': 'old'})
            status, headers, body = self.request(port, 'GET', '/radar?' + query)
        self.assertEqual(status, 302)
        destination = urlparse(headers['Location'])
        self.assertEqual(destination.scheme, 'https')
        self.assertEqual(destination.netloc, 'ajecv27.github.io')
        self.assertEqual(destination.path, '/seapoint-backend/')
        self.assertEqual(parse_qs(destination.query), {
            'lat': ['17.16'], 'lon': ['-61.835'],
            'name': ['North & Northwest Coast – Overview'], 'ui': ['world-20261114']})
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['Content-Length'], '0')
        self.assertEqual(body, b'')

    def test_head_and_no_query_use_the_same_world_map(self):
        with server() as port:
            for method in ('GET', 'HEAD'):
                with self.subTest(method=method):
                    status, headers, body = self.request(port, method, '/radar')
                    self.assertEqual(status, 302)
                    self.assertEqual(headers['Location'],
                                     'https://ajecv27.github.io/seapoint-backend/?ui=world-20261114')
                    self.assertEqual(body, b'')

    def test_untrusted_query_cannot_change_host_or_inject_headers(self):
        with server() as port:
            query = urlencode({'name': 'Antigua\r\nLocation: https://example.com',
                               'next': 'https://example.com', 'lon': ''})
            status, headers, _ = self.request(port, 'GET', '/radar?' + query)
        self.assertEqual(status, 302)
        destination = headers['Location']
        self.assertEqual(urlparse(destination).netloc, 'ajecv27.github.io')
        self.assertNotIn('\r', destination)
        self.assertNotIn('\n', destination)
        self.assertEqual(parse_qs(urlparse(destination).query, keep_blank_values=True)['lon'], [''])

    def test_unrelated_routes_still_use_the_existing_handler(self):
        with server() as port:
            status, _, _ = self.request(port, 'GET', '/not-a-route')
            head, headers, _ = self.request(port, 'HEAD', '/health')
        self.assertEqual(status, 404)
        self.assertEqual(head, 200)
        self.assertNotIn('Location', headers)


if __name__ == '__main__':
    unittest.main()
